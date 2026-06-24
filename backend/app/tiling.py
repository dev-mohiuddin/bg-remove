"""
Tiled inference module — enables processing of arbitrarily large images
(4K, 8K) without GPU OOM by splitting into overlapping tiles, running
inference on each, and blending the overlapping regions with feathering.

This is the same strategy remove.bg uses for high-resolution images.
"""

from __future__ import annotations

import logging
from typing import Callable, List, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Default tile size — must match the model's expected input.
DEFAULT_TILE_SIZE = 1024
# Overlap in pixels between adjacent tiles for seamless blending.
DEFAULT_OVERLAP = 128


def compute_tile_grid(
    width: int,
    height: int,
    tile_size: int = DEFAULT_TILE_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> List[Tuple[int, int, int, int]]:
    """
    Compute the grid of tiles covering the image.

    Returns a list of (x0, y0, x1, y1) crop coordinates.
    """
    step = tile_size - overlap
    tiles = []

    y = 0
    while y < height:
        y0 = y
        y1 = min(y0 + tile_size, height)
        x = 0
        while x < width:
            x0 = x
            x1 = min(x0 + tile_size, width)
            tiles.append((x0, y0, x1, y1))
            if x1 >= width:
                break
            x += step
        if y1 >= height:
            break
        y += step

    return tiles


def _feather_weight(size: int, overlap: int) -> np.ndarray:
    """
    Create a 1-D raised-cosine feathering weight for a tile edge.
    The first `overlap` and last `overlap` pixels are ramped.
    """
    w = np.ones(size, dtype=np.float32)
    if overlap > 0:
        ramp = 0.5 * (1 - np.cos(np.pi * np.arange(overlap) / overlap))
        w[:overlap] = ramp
        w[-overlap:] = ramp[::-1]
    return w


def _tile_weight(h: int, w: int, overlap: int) -> np.ndarray:
    """2-D feathering weight for a tile of size (h,w)."""
    wy = _feather_weight(h, overlap)
    wx = _feather_weight(w, overlap)
    return np.outer(wy, wx)


def tiled_inference(
    image: Image.Image,
    infer_fn: Callable[[Image.Image], Image.Image],
    tile_size: int = DEFAULT_TILE_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    progress_cb: Callable[[int, int], None] | None = None,
) -> Image.Image:
    """
    Run inference on large images by tiling.

    Args:
        image: PIL input image.
        infer_fn: function that takes a PIL crop and returns a PIL "L" mask
                  of the same size.
        tile_size: square tile dimension.
        overlap: overlap between tiles for blending.
        progress_cb: optional callback(completed, total) for progress reporting.

    Returns:
        PIL "L" mask at full resolution.
    """
    w, h = image.size

    # If the image fits in a single tile, just run inference directly.
    if w <= tile_size and h <= tile_size:
        if progress_cb:
            progress_cb(1, 1)
        return infer_fn(image)

    tiles = compute_tile_grid(w, h, tile_size, overlap)
    total = len(tiles)
    logger.info("Tiled inference: %dx%d -> %d tiles (tile=%d, overlap=%d)",
                w, h, total, tile_size, overlap)

    # Accumulators for weighted blending.
    alpha_sum = np.zeros((h, w), dtype=np.float32)
    weight_sum = np.zeros((h, w), dtype=np.float32)

    for i, (x0, y0, x1, y1) in enumerate(tiles):
        crop = image.crop((x0, y0, x1, y1))
        mask_crop = infer_fn(crop)
        mask_arr = np.asarray(mask_crop, dtype=np.float32) / 255.0

        th, tw = mask_arr.shape
        weight = _tile_weight(th, tw, min(overlap, th // 2, tw // 2))

        alpha_sum[y0:y1, x0:x1] += mask_arr * weight
        weight_sum[y0:y1, x0:x1] += weight

        if progress_cb:
            progress_cb(i + 1, total)

    # Normalize.
    weight_sum = np.maximum(weight_sum, 1e-8)
    alpha = alpha_sum / weight_sum
    alpha = np.clip(alpha, 0.0, 1.0)
    return Image.fromarray((alpha * 255).astype(np.uint8), mode="L")