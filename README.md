# ComfyUI_UltimateSDUpscale (fork)

Fork of [ssitu/ComfyUI_UltimateSDUpscale](https://github.com/ssitu/ComfyUI_UltimateSDUpscale), GPL-3.0, taken from upstream `main` at commit
[`a5547db`](https://github.com/ssitu/ComfyUI_UltimateSDUpscale/commit/a5547db) (2026-06-22). One source file is changed. The rest is upstream's
work, and bugs in the node itself belong upstream.

The fork exists because the node crashes on ComfyUI 0.44 and later:

```
AttributeError: 'ImageModelDescriptor' object has no attribute 'patcher'
```

Node IDs are unchanged (`UltimateSDUpscale`, `UltimateSDUpscaleNoUpscale`, `UltimateSDUpscaleCustomSample`, `UltimateSDUpscaleGuider`), so
existing workflows load as they are.

## The fix

ComfyUI 0.44 changed `ImageUpscaleWithModel.execute` to resolve its device through `upscale_model.patcher`. The built-in `UpscaleModelLoader`
sets that attribute. Every other way of producing an `UPSCALE_MODEL` does not, so the upscale fails before it starts.

`modules/upscaler.py` calls `ensure_upscale_patcher()` before upscaling:

1. If the model already has a patcher, nothing happens and the patcher is not re-wrapped.
2. If there is no patcher, one is attached with `CoreModelPatcher`.
3. If the running ComfyUI never reads `.patcher` (0.43 and older), the shim does nothing at all.

Whether ComfyUI reads `.patcher` is decided by `_execute_uses_patcher()`, which reads `ImageUpscaleWithModel.execute` and looks for `patcher`
in it. That is what keeps this one file working on both old and new ComfyUI. If a patcher cannot be created, it logs a warning and lets the
original code path run instead of raising.

Upstream ComfyUI has the equivalent fix in [Comfy-Org/ComfyUI#17567](https://github.com/Comfy-Org/ComfyUI/pull/17567) (open when this was
written; the crash report is [Comfy-Org/ComfyUI#17551](https://github.com/Comfy-Org/ComfyUI/issues/17551)). When that lands, this fork is
redundant.

No new Python dependencies. The patch uses `inspect`, `logging`, `comfy.model_management` and `comfy.model_patcher`, all of which ComfyUI
already ships.

## Installation

Remove any other copy of this node first. Two copies in `custom_nodes/` register the same node IDs and ComfyUI will show duplicates.

### ComfyUI Manager

1. [ComfyUI Manager](https://github.com/Comfy-Org/ComfyUI-Manager) must be installed.
2. Delete `ComfyUI/custom_nodes/comfyui_ultimatesdupscale` if it is there.
3. After launching ComfyUI, open ComfyUI Manager and select the "Custom Nodes Manager" option, then "Install via Git URL", and enter
   `https://github.com/lpnmqrpbmjx1064/comfyui-ultimatesdupscale-fork`
4. Follow any prompts to restart ComfyUI. Manager lists it under the repository name, `comfyui-ultimatesdupscale-fork`, and treats it as
   its own package rather than as a copy of upstream's.

### Using Git

1. Git must be installed on your system. Verify by running `git -v` in a terminal.
2. Enter the following command from the terminal starting in ComfyUI/custom_nodes/
    ```
    git clone https://github.com/lpnmqrpbmjx1064/comfyui-ultimatesdupscale-fork
    ```
3. Optional. This checks out the vendored script now instead of downloading it on the first run:
    ```
    git -C comfyui-ultimatesdupscale-fork submodule update --init --depth 1
    ```

### Manual Download

1. Download the latest zip from https://github.com/lpnmqrpbmjx1064/comfyui-ultimatesdupscale-fork/releases
2. Create a new folder in the `ComfyUI/custom_nodes/` directory to hold the extracted files, for example
   `ComfyUI/custom_nodes/comfyui-ultimatesdupscale-fork`.
3. Extract the contents of the zip file into that folder. The zip already contains `repositories/ultimate_sd_upscale/`, so nothing is
   downloaded on the first run.

### comfy-cli

Not on the registry yet, so `comfy node install comfyui_ultimatesdupscale` still installs upstream, not this fork.

The fork's registry package name is `ultimate-sd-upscale-fork`. ComfyUI Manager reads that name out of `pyproject.toml` to decide what a
package is, which is why the fork needed its own: while it still said `comfyui_ultimatesdupscale`, Manager matched the fork to upstream's
registry entry. Publishing is wired up in `.github/workflows/publish.yml` and needs `[tool.comfy].PublisherId` set to the fork owner's
publisher id, plus a `REGISTRY_ACCESS_TOKEN` secret. Until that is done, use one of the three options above.

## Usage

Nodes can be found in the node menu under `image/upscaling`.

Documentation for the nodes can be found in the [`js/docs/`](js/docs/) folder, or viewed within the application by right-clicking the
relevant node and selecting the info icon.

Details about most of the parameters can be found
[here](https://github.com/Coyote-A/ultimate-upscale-for-automatic1111/wiki/FAQ#parameters-descriptions).

Example workflows can be found in the [`example_workflows/`](example_workflows/) folder. They also show up in the ComfyUI application under
the Templates menu, in the Extensions section of the left sidebar, once the package is installed.

## Testing

The compatibility test runs ComfyUI's own upscale nodes on CPU, with a real spandrel descriptor that has no patcher, which is what any
non-built-in loader produces:

```
COMFY_DIR=/path/to/ComfyUI python test/comfy044_upscale_patch_test.py
```

It checks that the crash still reproduces on an unpatched descriptor, that the patch fixes it, that an existing patcher is left alone, that
single-tile and multi-tile upscales match direct inference pixel for pixel, and that all four nodes register. CI runs it on every push, and
runs `comfy node validate` (the registry's own check) alongside it.

Verified against ComfyUI 0.44.0 (commit `1332fabf`, 2026-11-07) on CPU with torch 2.15.0+cpu and spandrel 0.4.2. The crash itself came from
a ComfyUI 0.44.2 install on an Intel Arc B580 (XPU), where the fork was then tested in the application.

## AI assistance

The patch, the test, and the CI workflows in this fork were written by an AI agent: Hermes Agent, running `deepseek-v4.1-flash`. That is
worth saying plainly, so here is what the human part was.

- The human reported the crash, supplied the log from a ComfyUI 0.44.2 install, decided to fork rather than patch a local copy, and ran the
  fork in the application on an Arc B580.
- Everything else came from the agent: locating the changed ComfyUI code, writing the 60-line patch, reproducing the failure against
  ComfyUI's source before fixing it, writing the tests, and writing this file.

If you are going to rely on the patch, read it. The entire change is one file:

```
git diff a5547db -- modules/upscaler.py
```

## License

GPL-3.0, same as upstream. Node code and documentation are ssitu's. The vendored script in `repositories/ultimate_sd_upscale/` is
Coyote-A's, also GPL-3.0.

## References

* Ultimate Stable Diffusion Upscale script for the Automatic1111 Web UI: https://github.com/Coyote-A/ultimate-upscale-for-automatic1111
* ComfyUI: https://github.com/comfyanonymous/ComfyUI
* Upstream node: https://github.com/ssitu/ComfyUI_UltimateSDUpscale
