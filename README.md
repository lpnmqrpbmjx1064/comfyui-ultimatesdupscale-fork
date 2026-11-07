# ComfyUI_UltimateSDUpscale

> [!IMPORTANT]
> **This is a personal fork of [ssitu/ComfyUI_UltimateSDUpscale](https://github.com/ssitu/ComfyUI_UltimateSDUpscale)** (GPL-3.0),
> forked from upstream `main` at commit [`a5547db`](https://github.com/ssitu/ComfyUI_UltimateSDUpscale/commit/a5547db)
> (2026-06-22) with **one patch** on top. All other code is unmodified upstream work.
>
> Upstream: [github.com/ssitu/ComfyUI_UltimateSDUpscale](https://github.com/ssitu/ComfyUI_UltimateSDUpscale) — GPL-3.0.

## Fork patch: ComfyUI 0.44+ upscale-model compatibility

| # | File | Change | Why |
|---|------|--------|-----|
| 1 | `modules/upscaler.py` (+60 lines, no other file touched) | `ensure_upscale_patcher()` attaches a `CoreModelPatcher` when the `UPSCALE_MODEL` has none; `_execute_uses_patcher()` detects whether the running ComfyUI reads `.patcher` at all, so the same file also works on older ComfyUI | ComfyUI 0.44 changed `ImageUpscaleWithModel.execute` to resolve its device via `upscale_model.patcher`. Only the built-in `UpscaleModelLoader` attaches that attribute, so a model coming from any other loader made every USDU run fail with `AttributeError: 'ImageModelDescriptor' object has no attribute 'patcher'` |

Upstream context: [Comfy-Org/ComfyUI#17551](https://github.com/Comfy-Org/ComfyUI/issues/17551) (the crash report)
and [Comfy-Org/ComfyUI#17567](https://github.com/Comfy-Org/ComfyUI/pull/17567) (the equivalent fix inside ComfyUI,
still open when this patch was written).

The patch is designed to become inert rather than conflict:

- a model that already carries a patcher is left completely alone (identity preserved, no re-wrap);
- ComfyUI versions that never read `.patcher` skip the shim entirely (`_execute_uses_patcher()` is `False`);
- if a patcher cannot be created, it logs a warning and lets the original code path run unchanged.

## Install this fork

Replace **any** existing copy of `comfyui_ultimatesdupscale` first — two copies in `custom_nodes/`
register the same node IDs and ComfyUI will show duplicates.

**Option A — ComfyUI Manager (Git URL)**

1. Rename or delete `ComfyUI/custom_nodes/comfyui_ultimatesdupscale`.
2. ComfyUI Manager → *Custom Nodes Manager* → *Install via Git URL* →
   `https://github.com/lpnmqrpbmjx1064/ComfyUI_UltimateSDUpscale`
3. Restart ComfyUI.

**Option B — git clone**

```bash
cd ComfyUI/custom_nodes
mv comfyui_ultimatesdupscale comfyui_ultimatesdupscale.old   # if present
git clone https://github.com/lpnmqrpbmjx1064/ComfyUI_UltimateSDUpscale comfyui_ultimatesdupscale
# optional, avoids the first-run download of the vendored script:
git -C comfyui_ultimatesdupscale submodule update --init --depth 1
```

**Option C — zip drop-in**

Extract the release zip so that it lands as `ComfyUI/custom_nodes/comfyui_ultimatesdupscale/`
(the zip already contains `repositories/ultimate_sd_upscale/`, so nothing is downloaded on first run).

No extra Python dependencies: the patch only uses `inspect`, `logging`, `comfy.model_management`
and `comfy.model_patcher`, all of which ComfyUI already provides.

> [!NOTE]
> The registry entry (`comfy node install comfyui_ultimatesdupscale`) still resolves to **upstream**,
> not this fork — a fork cannot publish under upstream's `PublisherId`. Install this fork by Git URL or zip.

> **AI disclosure:** this patch was written with AI assistance (Hermes Agent) and verified against real
> ComfyUI 0.44 source: the failure was reproduced first (`AttributeError: 'ImageModelDescriptor' object
> has no attribute 'patcher'`), then the fix was exercised end-to-end on CPU — node registration, single-tile
> and multi-tile upscales, with output compared pixel-for-pixel against direct (unmanaged) inference.

---

[ComfyUI](https://github.com/comfyanonymous/ComfyUI) nodes for performing the image-to-image diffusion process on large images in tiles. This approach improves the details that is commonly found on upscaled images while reducing hardware requirements and maintaining an image size that the diffusion model is trained on.

## Installation


### Using Git
1. Git must be installed on your system. Verify by running `git -v` in a terminal.
2. Enter the following command from the terminal starting in ComfyUI/custom_nodes/
    ```
    git clone https://github.com/ssitu/ComfyUI_UltimateSDUpscale
    ```

### ComfyUI Manager
1. [ComfyUI Manager](https://github.com/Comfy-Org/ComfyUI-Manager) must be installed.
2. After launching ComfyUI, open ComfyUI Manager and select the "Custom Nodes Manager" option.
3. Search for "UltimateSDUpscale" and install the node. Select latest for the most up-to-date version.
4. Follow any prompts to restart ComfyUI.

### comfy-cli

1. [comfy-cli](https://github.com/Comfy-Org/comfy-cli) must be installed.
2. Run this command from the terminal: `comfy node install comfyui_ultimatesdupscale`

### Manual Download
1. Download the zip file from https://registry.comfy.org/nodes/comfyui_ultimatesdupscale to select the version you want, or obtain the current nightly version by clicking the green "Code" button on the GitHub repository page and selecting "Download ZIP".
2. Create a new folder in the `ComfyUI/custom_nodes/` directory to hold the extracted files (e.g. `ComfyUI/custom_nodes/ComfyUI_UltimateSDUpscale`).
3. Extract the contents of the zip file into the `ComfyUI/custom_nodes/ComfyUI_UltimateSDUpscale` folder.


## Usage

Nodes can be found in the node menu under `image/upscaling`.

Documentation for the nodes can be found in the [`js/docs/`](js/docs/) folder, or viewed within the application by right-clicking the relevant node and selecting the info icon.

Details about most of the parameters can be found [here](https://github.com/Coyote-A/ultimate-upscale-for-automatic1111/wiki/FAQ#parameters-descriptions).

Example workflows can be found in the [`example_workflows/`](example_workflows/) folder. You can also find them in the ComfyUI application under the Templates menu, scroll down the left sidebar to find the Extensions section, then selecting this repository.

## References
* Ultimate Stable Diffusion Upscale script for the Automatic1111 Web UI: https://github.com/Coyote-A/ultimate-upscale-for-automatic1111
* ComfyUI: https://github.com/comfyanonymous/ComfyUI