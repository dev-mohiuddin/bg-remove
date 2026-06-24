"""
Core background-removal pipeline.

Pipeline stages:
  1. Preprocess  — normalize input, upscale small images.
  2. Segmentation — BiRefNet (SOTA) via tiled inference for 4K support.
  3. Alpha Matting — ViTMatte / closed-form matting for pixel-perfect edges.
  4. Edge Refinement — guided filter + morphological cleanup.
  5. Composite   — apply alpha to produce RGBA PNG.

If BiRefNet is not available, falls back to rembg IS-Net so the service
never goes down.
"""

from __future__ import annotations

import io
import logging
import time
from typing import Callable

import numpy as np
from PIL import Image, ImageFilter

# Import onnxruntime shim FIRST to handle Python 3.14+ compatibility.
from . import onnx_shim  # noqa: F401

from .config import settings
from .matting import refine_alpha
from .tiling import tiled_inference

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fallback: rembg IS-Net (only used if BiRefNet ONNX is missing)
# ---------------------------------------------------------------------------

_rembg_session = None


def _get_rembg_session():
    global _rembg_session
    if _rembg_session is None:
        try:
            from rembg import new_session
            logger.warning("Falling back to rembg IS-Net (BiRefNet not found)")
            _rembg_session = new_session(settings.model_name)
        except Exception as exc:
            raise RuntimeError(f"Neither BiRefNet nor rembg available: {exc}") from exc
    return _rembg_session


def _rembg_mask(image: Image.Image) -> Image.Image:
    """Use rembg to produce a coarse mask (fallback path)."""
    from rembg import remove
    result = remove(image, session=_get_rembg_session(), alpha_matting=False)
    if result.mode == "RGBA":
        return result.split()[3]
    arr = np.asarray(result.convert("L"), dtype=np.float32) / 255.0
    return Image.fromarray((arr * 255).astype(np.uint8), mode="L")


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

def _segment(image: Image.Image, progress_cb: Callable[[int, int], None] | None = None) -> Image.Image:
    """Run the segmentation model (BiRefNet preferred) and return a soft mask."""
    try:
        from .models import birefnet

        if birefnet.is_available():
            logger.info("Using BiRefNet for segmentation")

            def infer_fn(crop: Image.Image) -> Image.Image:
                return birefnet.predict_mask(crop)

            return tiled_inference(
                image,
                infer_fn,
                tile_size=settings.tile_size,
                overlap=settings.tile_overlap,
                progress_cb=progress_cb,
            )
    except Exception:
        logger.exception("BiRefNet failed, falling back to rembg")

    if progress_cb:
        progress_cb(1, 1)
    return _rembg_mask(image)


# ---------------------------------------------------------------------------
# Edge refinement
# ---------------------------------------------------------------------------

def _refine_edges(alpha: np.ndarray) -> np.ndarray:
    """Post-process the alpha channel: remove specks, smooth seams, preserve soft edges."""
    alpha_img = Image.fromarray((alpha * 255).astype(np.uint8), mode="L")
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=0.5))

    opened = alpha_img.filter(ImageFilter.MinFilter(size=3))
    opened = opened.filter(ImageFilter.MaxFilter(size=3))

    orig = np.array(alpha_img, dtype=np.float32) / 255.0
    open_arr = np.array(opened, dtype=np.float32) / 255.0
    blend = np.where(orig < 0.05, open_arr, orig)
    return np.clip(blend, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Composite
# ---------------------------------------------------------------------------

def _composite(image: Image.Image, alpha: np.ndarray) -> Image.Image:
    """Apply the alpha channel to the original image -> RGBA."""
    if image.mode != "RGB":
        image = image.convert("RGB")
    rgba = image.convert("RGBA")
    alpha_u8 = (alpha * 255).clip(0, 255).astype(np.uint8)
    rgba.putalpha(Image.fromarray(alpha_u8, mode="L"))
    return rgba


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_image(
    image_bytes: bytes,
    progress_cb: Callable[[str, float], None] | None = None,
) -> bytes:
    """
    Full background-removal pipeline.

    Args:
        image_bytes: raw image file bytes.
        progress_cb: optional callback(stage_name, fraction 0..1).

    Returns:
        PNG bytes of the RGBA result.
    """
    t0 = time.time()

    if progress_cb:
        progress_cb("loading", 0.02)
    try:
        input_image = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise ValueError(f"Cannot open image: {exc}") from exc

    original_size = input_image.size
    logger.info("Processing image: %s, size=%s", input_image.mode, original_size)

    if input_image.mode == "P":
        input_image = input_image.convert("RGBA")
    if input_image.mode not in ("RGB", "RGBA"):
        input_image = input_image.convert("RGB")

    min_dim = min(input_image.size)
    upscaled = False
    if min_dim < 800:
        scale = 800 / min_dim
        new_size = (int(input_image.width * scale), int(input_image.height * scale))
        input_image = input_image.resize(new_size, Image.LANCZOS)
        upscaled = True

    rgb_image = input_image.convert("RGB")

    # --- Stage 2: Segmentation (BiRefNet, tiled) ---
    if progress_cb:
        progress_cb("segmenting", 0.10)

    def seg_progress(done: int, total: int):
        if progress_cb and total > 0:
            frac = 0.10 + 0.50 * (done / total)
            progress_cb("segmenting", frac)

    mask_image = _segment(rgb_image, progress_cb=seg_progress)
    coarse_mask = np.asarray(mask_image, dtype=np.float32) / 255.0

    # --- Stage 3: Alpha matting ---
    if progress_cb:
        progress_cb("matting", 0.65)

    img_arr = np.asarray(rgb_image, dtype=np.float32) / 255.0
    alpha = refine_alpha(
        img_arr,
        coarse_mask,
        use_vitmatte=settings.use_vitmatte,
        erode_radius=settings.trimap_erode_radius,
        dilate_radius=settings.trimap_dilate_radius,
    )

    # --- Stage 4: Edge refinement ---
    if progress_cb:
        progress_cb("refining", 0.85)
    alpha = _refine_edges(alpha)

    # --- Stage 5: Composite ---
    if progress_cb:
        progress_cb("compositing", 0.92)
    result = _composite(rgb_image, alpha)

    if upscaled:
        result = result.resize(original_size, Image.LANCZOS)

    if progress_cb:
        progress_cb("encoding", 0.96)
    buf = io.BytesIO()
    result.save(buf, format="PNG", optimize=False, compress_level=1)
    png_bytes = buf.getvalue()

    elapsed = time.time() - t0
    logger.info("Pipeline complete in %.2fs (%d KB out)", elapsed, len(png_bytes) // 1024)
    if progress_cb:
        progress_cb("done", 1.0)
    return png_bytes


def process_image_to_mask(image_bytes: bytes) -> bytes:
    """Produce just the alpha mask as a grayscale PNG (for frontend touch-up)."""
    try:
        input_image = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise ValueError(f"Cannot open image: {exc}") from exc

    if input_image.mode not in ("RGB", "RGBA"):
        input_image = input_image.convert("RGB")
    rgb_image = input_image.convert("RGB")

    mask_image = _segment(rgb_image)
    coarse_mask = np.asarray(mask_image, dtype=np.float32) / 255.0
    img_arr = np.asarray(rgb_image, dtype=np.float32) / 255.0
    alpha = refine_alpha(img_arr, coarse_mask, use_vitmatte=settings.use_vitmatte)

    buf = io.BytesIO()
    Image.fromarray((alpha * 255).astype(np.uint8), mode="L").save(buf, format="PNG")
    return buf.getvalue()
