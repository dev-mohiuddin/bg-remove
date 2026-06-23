

import io
import logging

import numpy as np
from PIL import Image, ImageFilter
from rembg import new_session, remove

from .config import settings

logger = logging.getLogger(__name__)


_session = None


def _get_session():
    
    global _session
    if _session is None:
        logger.info("Loading rembg model: %s", settings.model_name)
        _session = new_session(settings.model_name)
        logger.info("Model loaded successfully")
    return _session


def _refine_mask(rgba_image: Image.Image) -> Image.Image:
    
    r, g, b, a = rgba_image.split()
    alpha_arr = np.array(a, dtype=np.float32)


    alpha_arr[alpha_arr < 15] = 0

    alpha_arr[alpha_arr > 240] = 255


    alpha_refined = Image.fromarray(alpha_arr.astype(np.uint8), mode="L")
    alpha_refined = alpha_refined.filter(ImageFilter.GaussianBlur(radius=0.6))

    rgba_image.putalpha(alpha_refined)
    return rgba_image


def remove_background(image_bytes: bytes) -> bytes:
    
    try:
        input_image = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise ValueError(f"Cannot open image: {exc}") from exc


    original_size = input_image.size


    if input_image.mode == "P":
        input_image = input_image.convert("RGBA")
    elif input_image.mode not in ("RGB", "RGBA"):
        input_image = input_image.convert("RGB")


    min_dim = min(input_image.size)
    upscaled = False
    if min_dim < 800:
        scale = 800 / min_dim
        new_size = (int(input_image.width * scale), int(input_image.height * scale))
        input_image = input_image.resize(new_size, Image.LANCZOS)
        upscaled = True

    session = _get_session()


    result: Image.Image = remove(
        input_image,
        session=session,
        alpha_matting=True,

        alpha_matting_foreground_threshold=245,

        alpha_matting_background_threshold=8,

        alpha_matting_erode_size=5,
    )


    result = _refine_mask(result)


    if upscaled:
        result = result.resize(original_size, Image.LANCZOS)


    output_buffer = io.BytesIO()
    result.save(output_buffer, format="PNG", optimize=False, compress_level=1)
    output_buffer.seek(0)

    return output_buffer.getvalue()
