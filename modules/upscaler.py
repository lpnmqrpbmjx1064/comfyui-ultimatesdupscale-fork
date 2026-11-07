import inspect
import logging

from PIL import Image
from usdu_utils import tensor_to_pil, pil_to_tensor
from comfy_extras.nodes_upscale_model import ImageUpscaleWithModel
from modules import shared

if (not hasattr(Image, 'Resampling')):  # For older versions of Pillow
    Image.Resampling = Image

logger = logging.getLogger(__name__)


def _execute_uses_patcher() -> bool:
    """Does this ComfyUI resolve the device through ``upscale_model.patcher``?

    ComfyUI 0.44 moved upscale-model loading onto ``CoreModelPatcher``; older releases never
    touch that attribute. Detect it instead of pinning to a version, so the same file works on
    both. If the source cannot be introspected, assume the newer behaviour.
    """
    try:
        return "patcher" in inspect.getsource(ImageUpscaleWithModel.execute)
    except (OSError, TypeError):  # compiled/zipped install, source unavailable
        return True


def ensure_upscale_patcher(model):
    """Attach a model patcher when the upscale model arrived without one.

    ComfyUI's ``UpscaleModelLoader`` wraps the loaded spandrel ``ImageModelDescriptor`` in a
    ``CoreModelPatcher`` and stores it as ``model.patcher``. Any other loader (and any code
    path that builds its own descriptor) leaves that attribute missing, and ComfyUI 0.44's
    ``ImageUpscaleWithModel.execute`` then raises
    ``AttributeError: 'ImageModelDescriptor' object has no attribute 'patcher'``.

    Mirror the built-in loader so those models can be upscaled. A patcher that is already
    present (including its device and storage policy) is never replaced.

    Returns True when a patcher was added.
    """
    if model is None or getattr(model, "patcher", None) is not None:
        return False

    try:
        import comfy.model_management as model_management
        import comfy.model_patcher as model_patcher

        # CoreModelPatcher is current; older releases only expose ModelPatcher.
        patcher_cls = getattr(model_patcher, "CoreModelPatcher", None) or model_patcher.ModelPatcher
        model.patcher = patcher_cls(
            model.model,
            load_device=model_management.get_torch_device(),
            offload_device=model_management.unet_offload_device(),
        )
        logger.info(
            "USDU: attached a model patcher to %s (the loader provided none)",
            type(model).__name__,
        )
        return True
    except Exception as exc:  # pragma: no cover - depends on ComfyUI internals
        logger.warning(
            "USDU: could not attach a model patcher to %s: %s", type(model).__name__, exc
        )
        return False


class Upscaler:

    def upscale(self, img: Image, scale, selected_model: str = None):
        if scale == 1.0:
            return img
        if (shared.actual_upscaler is None):
            return img.resize((img.width * scale, img.height * scale), Image.Resampling.LANCZOS)
        if "execute" in dir(ImageUpscaleWithModel):  
            # V3 schema: https://github.com/comfyanonymous/ComfyUI/pull/10149
            if _execute_uses_patcher():
                ensure_upscale_patcher(shared.actual_upscaler)
            (upscaled,) = ImageUpscaleWithModel.execute(shared.actual_upscaler, shared.batch_as_tensor)
        else:
            (upscaled,) = ImageUpscaleWithModel().upscale(shared.actual_upscaler, shared.batch_as_tensor)
        shared.batch = [tensor_to_pil(upscaled, i) for i in range(len(upscaled))]
        return shared.batch[0]


class UpscalerData:
    name = ""
    data_path = ""

    def __init__(self):
        self.scaler = Upscaler()
