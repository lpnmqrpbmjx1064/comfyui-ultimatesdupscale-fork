"""ComfyUI 0.44+ upscale-model compatibility test.

ComfyUI 0.44 resolves the upscaler device through `upscale_model.patcher`. Only the built-in
`UpscaleModelLoader` attaches that attribute, so any other `UPSCALE_MODEL` source made every
run fail with:

    AttributeError: 'ImageModelDescriptor' object has no attribute 'patcher'

This test drives ComfyUI's real `comfy_extras.nodes_upscale_model` code on CPU, with a real
spandrel descriptor that has no patcher, through this repository's `modules/upscaler.py`.

Usage:
    COMFY_DIR=/path/to/ComfyUI python test/comfy044_upscale_patch_test.py

COMFY_DIR defaults to a sibling `ComfyUI` directory next to this repository.
"""

import os
import pathlib
import sys

REPO_DIR = pathlib.Path(__file__).resolve().parent.parent
COMFY_DIR = pathlib.Path(os.environ.get("COMFY_DIR", REPO_DIR.parent / "ComfyUI")).resolve()
if not (COMFY_DIR / "comfy_extras" / "nodes_upscale_model.py").is_file():
    print(f"BLOCKED: no ComfyUI checkout at {COMFY_DIR} (set COMFY_DIR)")
    sys.exit(2)

# ComfyUI imports its own top-level modules (folder_paths, comfy.*), and picks its device at
# import time, so the working directory and arguments have to be set up before those imports.
sys.path.insert(0, str(COMFY_DIR))
os.chdir(COMFY_DIR)
sys.argv = ["main.py", "--cpu"]

import comfy.options  # noqa: E402

comfy.options.enable_args_parsing()

import numpy as np  # noqa: E402
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
from spandrel import Architecture, ImageModelDescriptor  # noqa: E402

# Import ComfyUI's core before this repository: ComfyUI loads built-in nodes first, and this
# package purges modules it newly imported (see __init__.py) which otherwise makes torch
# re-register its dynamo cache artifacts.
import comfy.model_management  # noqa: E402,F401
import comfy.model_patcher  # noqa: E402,F401
import comfy.utils  # noqa: E402,F401
from comfy_extras.nodes_upscale_model import ImageUpscaleWithModel  # noqa: E402

sys.path.insert(0, str(REPO_DIR))
from PIL import Image  # noqa: E402
from modules import shared, upscaler  # noqa: E402
from usdu_utils import tensor_to_pil  # noqa: E402

FAILURES = []


def check(name, condition, detail=""):
    print(f"  [{'PASS' if condition else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not condition:
        FAILURES.append(name)


class UpscaleNet(nn.Module):
    """Stand-in for a real upscale network: 2x nearest neighbour, 3 channels in and out."""

    def forward(self, x):
        return torch.nn.functional.interpolate(x, scale_factor=2, mode="nearest")


class UpscaleArch(Architecture):
    def __init__(self):
        super().__init__(id="test", detect=lambda state_dict: True, name="Test")

    def load(self, state_dict):
        return UpscaleNet()


def make_descriptor():
    """A genuine spandrel descriptor, as a third-party UPSCALE_MODEL loader would return it."""
    return ImageModelDescriptor(UpscaleNet(), {}, UpscaleArch(), "SR", [], False, False, 2, 3, 3, None)


def upscale_via_usdu(descriptor, size):
    torch.manual_seed(0)
    image = torch.rand(1, size, size, 3)
    shared.actual_upscaler = descriptor
    shared.batch_as_tensor = image
    shared.batch = [Image.new("RGB", (size, size))]
    result = upscaler.Upscaler().upscale(shared.batch[0], 2.0)
    with torch.no_grad():
        direct = tensor_to_pil(descriptor(image.movedim(-1, -3)).movedim(-3, -1).clamp(0, 1), 0)
    identical = np.array_equal(np.asarray(result), np.asarray(direct))
    return result, identical


def main():
    print(f"ComfyUI: {COMFY_DIR}")
    print(f"this repo: {REPO_DIR}")
    print(f"torch {torch.__version__}\n")

    print("the failure being guarded against")
    bare = make_descriptor()
    check("descriptor starts without a patcher", not hasattr(bare, "patcher"))
    try:
        ImageUpscaleWithModel.execute(bare, torch.rand(1, 16, 16, 3))
    except AttributeError as exc:
        check("ComfyUI raises the patcher AttributeError without the fix", "patcher" in str(exc), str(exc))
    else:
        check("ComfyUI raises the patcher AttributeError without the fix", False,
              "this ComfyUI does not read .patcher; the shim is unnecessary here")

    print("\npatcher handling")
    execute_source = pathlib.Path(
        COMFY_DIR / "comfy_extras" / "nodes_upscale_model.py").read_text(encoding="utf-8")
    detects_correctly = upscaler._execute_uses_patcher() == ("patcher" in execute_source)
    check("detection matches whether this ComfyUI reads .patcher", detects_correctly,
          f"_execute_uses_patcher() = {upscaler._execute_uses_patcher()}")

    already = make_descriptor()
    import comfy.model_management as model_management
    already.patcher = comfy.model_patcher.CoreModelPatcher(
        already.model,
        load_device=model_management.get_torch_device(),
        offload_device=model_management.unet_offload_device(),
    )
    existing = already.patcher
    check("an existing patcher is not replaced", upscaler.ensure_upscale_patcher(already) is False)
    check("an existing patcher keeps its identity", already.patcher is existing)

    none_patcher = make_descriptor()
    none_patcher.patcher = None
    check("patcher = None gets one", upscaler.ensure_upscale_patcher(none_patcher) is True)

    print("\nend to end through modules/upscaler.py")
    result, identical = upscale_via_usdu(make_descriptor(), 32)
    check("single tile upscales", result.size == (64, 64), str(result.size))
    check("output matches direct inference", identical)

    # 600x450 crosses ComfyUI's 512 tile boundary, so tiled_scale has to stitch tiles.
    torch.manual_seed(1)
    descriptor = make_descriptor()
    shared.actual_upscaler = descriptor
    shared.batch_as_tensor = torch.rand(1, 450, 600, 3)
    shared.batch = [Image.new("RGB", (600, 450))]
    result = upscaler.Upscaler().upscale(shared.batch[0], 2.0)
    check("multi tile upscales", result.size == (1200, 900), str(result.size))
    check("multi tile output matches direct inference",
          np.array_equal(np.asarray(result),
                         np.asarray(tensor_to_pil(
                             descriptor(shared.batch_as_tensor.movedim(-1, -3)).movedim(-3, -1).clamp(0, 1), 0))))

    print("\nnode registration")
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "comfyui_ultimatesdupscale", str(REPO_DIR / "__init__.py"),
        submodule_search_locations=[str(REPO_DIR)],
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules["comfyui_ultimatesdupscale"] = package
    spec.loader.exec_module(package)
    registered = set(package.NODE_CLASS_MAPPINGS)
    check("UltimateSDUpscale is registered", "UltimateSDUpscale" in registered, ", ".join(sorted(registered)))

    print(f"\n{len(FAILURES)} failure(s)" + ("" if not FAILURES else ": " + "; ".join(FAILURES)))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
