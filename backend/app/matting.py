"""
Alpha Matting module — converts a coarse binary/soft mask into a
pixel-perfect alpha channel with fractional transparency.

Pipeline:
  1. Build a trimap from the BiRefNet mask (foreground / background /
     unknown region).
  2. Run closed-form matting (Levin et al. 2008) on the unknown region
     to solve the alpha compositing equation  I = aF + (1-a)B.
  3. If ViTMatte ONNX is available, use it as a learned refiner on the
     unknown band for even higher fidelity.

This is the same class of technique that remove.bg uses internally to
recover wispy hair, motion blur, and semi-transparent fabric edges.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Trimap generation
# ---------------------------------------------------------------------------

def build_trimap(
    mask: np.ndarray,
    erode_radius: int = 6,
    dilate_radius: int = 18,
    threshold_low: float = 0.1,
    threshold_high: float = 0.9,
) -> np.ndarray:
    """
    Build a trimap from a soft mask.

    Args:
        mask: float32 array [0,1], shape (H,W).
        erode_radius: pixels to erode the foreground for the unknown band.
        dilate_radius: pixels to dilate the foreground for the unknown band.
        threshold_low: below this -> definite background.
        threshold_high: above this -> definite foreground.

    Returns:
        uint8 trimap: 0 = background, 128 = unknown, 255 = foreground.
    """
    # Binarize.
    fg = (mask >= threshold_high).astype(np.uint8) * 255
    bg = (mask <= threshold_low).astype(np.uint8) * 255

    # Erode foreground to find definite-FG core.
    fg_img = Image.fromarray(fg, mode="L")
    fg_eroded = fg_img.filter(
        ImageFilter.MinFilter(size=erode_radius * 2 + 1)
    )

    # Dilate foreground to find the outer boundary.
    fg_dilated = fg_img.filter(
        ImageFilter.MaxFilter(size=dilate_radius * 2 + 1)
    )

    fg_eroded_arr = np.array(fg_eroded)
    fg_dilated_arr = np.array(fg_dilated)

    trimap = np.full_like(mask, 128, dtype=np.uint8)  # unknown by default
    trimap[fg_eroded_arr > 0] = 255                    # definite FG
    trimap[fg_dilated_arr == 0] = 0                    # definite BG
    return trimap


# ---------------------------------------------------------------------------
# Closed-form matting (Levin, Lischinski, Weiss 2008)
# ---------------------------------------------------------------------------

def _solve_linear_system(
    laplacian_rows: list[np.ndarray],
    confidence: np.ndarray,
    alpha_init: np.ndarray,
    lambda_val: float = 100.0,
) -> np.ndarray:
    """
    Solve the closed-form matting linear system for a small window.

    For each unknown pixel we solve:
        (L + lambda * D) a = lambda * c
    where L is the matting Laplacian, D is a diagonal confidence matrix,
    and c is the known alpha values.
    """
    # This is a simplified per-window solver; for full images we use the
    # sparse approach below.
    pass


def closed_form_matting(
    image: np.ndarray,
    trimap: np.ndarray,
    window_radius: int = 1,
    epsilon: float = 1e-7,
) -> np.ndarray:
    """
    Closed-form alpha matting (Levin et al.).

    Solves for alpha that minimises the matting Laplacian cost:
        alpha = argmin  alpha^T L alpha  s.t.  alpha = known on trimap.

    Args:
        image: float32 RGB image, values [0,1], shape (H,W,3).
        trimap: uint8 trimap (0=BG, 128=unknown, 255=FG).
        window_radius: radius of the local window (default 1 -> 3x3).
        epsilon: regularisation for the colour-line model.

    Returns:
        float32 alpha in [0,1], shape (H,W).
    """
    h, w = image.shape[:2]
    image = image.astype(np.float32)

    # Known alpha from trimap.
    known_fg = trimap == 255
    known_bg = trimap == 0
    unknown = trimap == 128

    alpha = np.zeros((h, w), dtype=np.float32)
    alpha[known_fg] = 1.0
    alpha[known_bg] = 0.0

    # If there is nothing unknown, return early.
    if not np.any(unknown):
        return alpha

    # Build the sparse matting Laplacian.
    try:
        from scipy.sparse import lil_matrix, csr_matrix
        from scipy.sparse.linalg import cg
    except ImportError:
        logger.warning("scipy not available; falling back to guided-filter matting")
        return _guided_filter_matting(image, trimap, alpha, window_radius, epsilon)

    window_size = (2 * window_radius + 1) ** 2
    n = h * w

    # Build the Laplacian as a sparse matrix.
    lap = lil_matrix((n, n), dtype=np.float32)

    # For each pixel, compute the window covariance.
    img_flat = image.reshape(-1, 3)

    # Precompute per-window mean and covariance.
    for y in range(h):
        for x in range(w):
            idx = y * w + x
            y0 = max(0, y - window_radius)
            y1 = min(h, y + window_radius + 1)
            x0 = max(0, x - window_radius)
            x1 = min(w, x + window_radius + 1)

            window = image[y0:y1, x0:x1].reshape(-1, 3)
            k = window.shape[0]
            mean = window.mean(axis=0)
            cov = np.cov(window, rowvar=False) + (epsilon / k) * np.eye(3)

            # Inverse of (cov + epsilon/k * I).
            inv_cov = np.linalg.inv(cov)

            for j in range(k):
                dy = y0 + j // (x1 - x0)
                dx = x0 + j % (x1 - x0)
                jdx = dy * w + dx
                diff = window[j] - mean
                val = 0.5 * diff @ inv_cov @ diff
                lap[idx, jdx] += val

    lap = lap.tocsr()

    # Add confidence constraints.
    confidence = np.zeros(n, dtype=np.float32)
    confidence[known_fg.reshape(-1)] = 1.0
    confidence[known_bg.reshape(-1)] = 1.0

    D = lil_matrix((n, n), dtype=np.float32)
    for i in range(n):
        if confidence[i] > 0:
            D[i, i] = 1.0
    D = D.tocsr()

    A = lap + 100.0 * D
    b = 100.0 * confidence

    # Solve via conjugate gradient.
    alpha_flat, _ = cg(A, b, x0=alpha.reshape(-1), maxiter=200, tol=1e-5)
    alpha = np.clip(alpha_flat.reshape(h, w), 0.0, 1.0)
    return alpha


def _guided_filter_matting(
    image: np.ndarray,
    trimap: np.ndarray,
    alpha_init: np.ndarray,
    radius: int = 1,
    epsilon: float = 1e-7,
) -> np.ndarray:
    """
    Fast approximation of closed-form matting using the guided filter
    (He et al. 2013).  This is used when scipy is unavailable and is
    also much faster for large images.
    """
    # The guided filter computes a local linear model:
    #   a_i = cov(I, p) / (var(I) + epsilon)
    #   b_i = mean(p) - a_i * mean(I)
    # then filters alpha_init guided by the image.
    guided = _guided_filter(
        image[:, :, 0], alpha_init, radius=radius * 8, epsilon=epsilon * 100
    )
    # Blend with the initial alpha based on trimap confidence.
    known = (trimap == 255) | (trimap == 0)
    alpha = np.where(known, alpha_init, guided)
    return np.clip(alpha, 0.0, 1.0)


def _guided_filter(
    guide: np.ndarray,
    src: np.ndarray,
    radius: int = 8,
    epsilon: float = 1e-3,
) -> np.ndarray:
    """Box-filter based guided filter (single channel)."""
    try:
        import cv2
        return cv2.guidedFilter(guide.astype(np.float32), src.astype(np.float32), radius, epsilon)
    except ImportError:
        return _box_guided_filter(guide, src, radius, epsilon)


def _box_guided_filter(
    guide: np.ndarray,
    src: np.ndarray,
    radius: int,
    epsilon: float,
) -> np.ndarray:
    """Pure-numpy guided filter using box mean."""
    from PIL import Image as PILImage, ImageFilter

    def box_mean(arr: np.ndarray, r: int) -> np.ndarray:
        img = PILImage.fromarray((arr * 255).clip(0, 255).astype(np.uint8))
        # Use a mean filter approximation.
        return np.array(img.filter(ImageFilter.BoxBlur(radius=r)), dtype=np.float32) / 255.0

    mean_i = box_mean(guide, radius)
    mean_p = box_mean(src, radius)
    mean_ip = box_mean(guide * src, radius)
    mean_ii = box_mean(guide * guide, radius)

    cov_ip = mean_ip - mean_i * mean_p
    var_i = mean_ii - mean_i * mean_i

    a = cov_ip / (var_i + epsilon)
    b = mean_p - a * mean_i

    mean_a = box_mean(a, radius)
    mean_b = box_mean(b, radius)

    return mean_a * guide + mean_b


# ---------------------------------------------------------------------------
# ViTMatte learned refiner (optional, highest fidelity)
# ---------------------------------------------------------------------------

_vitmatte_session = None

def _resolve_vitmatte_path() -> Optional[str]:
    env_path = os.environ.get("VITMATTE_ONNX_PATH", "")
    if env_path and Path(env_path).exists():
        return env_path
    candidates = [
        Path(__file__).resolve().parent.parent / "models" / "vitmatte.onnx",
        Path("/models/vitmatte.onnx"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def get_vitmatte_session():
    global _vitmatte_session
    if _vitmatte_session is not None:
        return _vitmatte_session
    from . import onnx_shim
    ort = onnx_shim.get_session()
    if ort is None:
        return None
    path = _resolve_vitmatte_path()
    if path is None:
        return None
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    _vitmatte_session = ort.InferenceSession(path, providers=providers)
    logger.info("ViTMatte loaded from %s", path)
    return _vitmatte_session


def vitmatte_refine(
    image: np.ndarray,
    trimap: np.ndarray,
) -> Optional[np.ndarray]:
    """
    Run ViTMatte on the image + trimap to produce a refined alpha.

    Args:
        image: float32 RGB [0,1] (H,W,3).
        trimap: uint8 trimap.

    Returns:
        float32 alpha [0,1] (H,W) or None if ViTMatte is unavailable.
    """
    sess = get_vitmatte_session()
    if sess is None:
        return None

    h, w = image.shape[:2]
    # ViTMatte typically uses 512x512.
    target = 512
    img_resized = np.array(
        Image.fromarray((image * 255).astype(np.uint8)).resize((target, target), Image.BILINEAR),
        dtype=np.float32,
    ) / 255.0
    trimap_resized = np.array(
        Image.fromarray(trimap).resize((target, target), Image.NEAREST),
        dtype=np.float32,
    ) / 255.0

    # Normalize.
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img_norm = (img_resized - mean) / std
    img_chw = img_norm.transpose(2, 0, 1)[None]
    trimap_chw = trimap_resized[None, None]

    inputs = {}
    for inp in sess.get_inputs():
        if "trimap" in inp.name.lower() or inp.name in ("trimap", "t"):
            inputs[inp.name] = trimap_chw
        else:
            inputs[inp.name] = img_chw

    out = sess.run(None, inputs)[0].squeeze()
    out = np.clip(out, 0.0, 1.0)
    # Resize back.
    out_img = Image.fromarray((out * 255).astype(np.uint8), mode="L")
    out_img = out_img.resize((w, h), Image.BILINEAR)
    return np.array(out_img, dtype=np.float32) / 255.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def refine_alpha(
    image: np.ndarray,
    coarse_mask: np.ndarray,
    use_vitmatte: bool = True,
    erode_radius: int = 6,
    dilate_radius: int = 18,
) -> np.ndarray:
    """
    Full alpha-matting pipeline.

    Args:
        image: float32 RGB [0,1] (H,W,3).
        coarse_mask: float32 [0,1] (H,W) from BiRefNet.
        use_vitmatte: try ViTMatte first if available.
        erode_radius / dilate_radius: trimap band widths.

    Returns:
        float32 alpha [0,1] (H,W).
    """
    trimap = build_trimap(
        coarse_mask,
        erode_radius=erode_radius,
        dilate_radius=dilate_radius,
    )

    # Try ViTMatte first (learned, highest fidelity).
    if use_vitmatte:
        vit = vitmatte_refine(image, trimap)
        if vit is not None:
            logger.info("Alpha refined with ViTMatte")
            # Preserve definite FG/BG from trimap.
            vit[trimap == 255] = 1.0
            vit[trimap == 0] = 0.0
            return vit

    # Fall back to closed-form / guided-filter matting.
    logger.info("Alpha refined with closed-form/guided-filter matting")
    alpha = closed_form_matting(image, trimap)
    return alpha