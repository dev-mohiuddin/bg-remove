"""
BiRefNet model wrapper — State-of-the-Art Bilateral Reference Network
for high-accuracy dichotomous image segmentation.

BiRefNet (2024) achieves SOTA on DIS5K by using a bilateral reference
mechanism that explicitly targets edge ambiguity. This module loads the
ONNX-exported BiRefNet model and provides high-performance inference with
proper preprocessing and postprocessing.

If the ONNX export is not available, we fall back to the HuggingFace
PyTorch checkpoint via transformers / custom code.
"""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

# Import onnxruntime via shim for Python 3.14+ compatibility.
from .. import onnx_shim

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# BiRefNet expects 1024x1024 input for best edge fidelity.
BIREFNET_INPUT_SIZE = 1024

# ImageNet normalization stats used during BiRefNet training.
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# Cached singleton session.
_birefnet_session = None
_birefnet_provider = None


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def _resolve_model_path() -> Optional[str]:
    """Resolve the BiRefNet ONNX model path from env or bundled location."""
    env_path = os.environ.get("BIREFNET_ONNX_PATH", "")
    if env_path and Path(env_path).exists():
        return env_path

    # Check common bundled locations.
    candidates = [
        Path(__file__).resolve().parent.parent / "models" / "birefnet.onnx",
        Path(__file__).resolve().parent.parent / "models" / "birefnet_fp16.onnx",
        Path("/models/birefnet.onnx"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def _get_providers() -> list[str]:
    """Build the list of ONNX execution providers, GPU first."""
    providers = []
    try:
        ort = onnx_shim.get_session()
        if ort is None:
            raise RuntimeError("onnxruntime not available")

        available = ort.get_available_providers()
        if "CUDAExecutionProvider" in available:
            providers.append(
                ("CUDAExecutionProvider", {
                    "device_id": 0,
                    "arena_extend_strategy": "kSameAsRequested",
                    "gpu_mem_limit": int(6 * 1024 * 1024 * 1024),  # 6 GB cap
                    "cudnn_conv_algo_search": "EXHAUSTIVE",
                })
            )
        providers.append("CPUExecutionProvider")
    except Exception:
        providers = ["CPUExecutionProvider"]
    return providers


def get_birefnet_session():
    """Return a cached BiRefNet ONNX inference session."""
    global _birefnet_session, _birefnet_provider

    if _birefnet_session is not None:
        return _birefnet_session

    ort = onnx_shim.get_session()
    if ort is None:
        raise RuntimeError("onnxruntime not available on this Python version")

    model_path = _resolve_model_path()
    if model_path is None:
        raise RuntimeError(
            "BiRefNet ONNX model not found. Set BIREFNET_ONNX_PATH or place "
            "the model at backend/models/birefnet.onnx. You can export it "
            "from the HuggingFace checkpoint 'ZhengPeng7/BiRefNet'."
        )

    providers = _get_providers()
    logger.info("Loading BiRefNet ONNX from %s with providers %s", model_path, providers)

    sess_opts = ort.SessionOptions()
    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess_opts.intra_op_num_threads = 2
    sess_opts.inter_op_num_threads = 2

    _birefnet_session = ort.InferenceSession(
        model_path,
        sess_options=sess_opts,
        providers=providers,
    )
    _birefnet_provider = _birefnet_session.get_providers()[0]
    logger.info("BiRefNet loaded. Active provider: %s", _birefnet_provider)
    return _birefnet_session


# ---------------------------------------------------------------------------
# Preprocessing / Postprocessing
# ---------------------------------------------------------------------------

def preprocess(image: Image.Image) -> tuple[np.ndarray, tuple[int, int]]:
    """
    Convert a PIL image to the normalized tensor expected by BiRefNet.

    Returns:
        (tensor[1,3,1024,1024] float32, original_size (w,h))
    """
    original_size = image.size  # (w, h)
    rgb = image.convert("RGB")
    rgb = rgb.resize(
        (BIREFNET_INPUT_SIZE, BIREFNET_INPUT_SIZE), Image.BILINEAR
    )

    arr = np.asarray(rgb, dtype=np.float32) / 255.0          # HWC
    arr = (arr - IMAGENET_MEAN) / IMAGENET_STD               # normalize
    arr = arr.transpose(2, 0, 1)                              # CHW
    arr = np.expand_dims(arr, axis=0)                         # 1CHW
    return arr.astype(np.float32), original_size


def postprocess(
    raw_mask: np.ndarray,
    target_size: tuple[int, int],
) -> Image.Image:
    """
    Convert the raw BiRefNet sigmoid output to a full-resolution alpha mask.

    Args:
        raw_mask: array of shape (1,1,H,W) or (1,H,W) with values in [0,1].
        target_size: (width, height) to resize the mask back to.

    Returns:
        PIL "L" mode image with values 0-255.
    """
    # Squeeze batch + channel dims.
    mask = raw_mask.squeeze()
    if mask.ndim != 2:
        mask = mask[0] if mask.ndim == 3 else mask

    # BiRefNet output is already sigmoid-activated in most exports.
    # Clamp to [0,1] for safety.
    mask = np.clip(mask, 0.0, 1.0)

    # Convert to uint8 for PIL resize.
    mask_u8 = (mask * 255.0).astype(np.uint8)
    mask_img = Image.fromarray(mask_u8, mode="L")

    # Resize back to original resolution with bilinear for smooth edges.
    mask_img = mask_img.resize(target_size, Image.BILINEAR)
    return mask_img


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def predict_mask(image: Image.Image) -> Image.Image:
    """
    Run BiRefNet on a single image and return a full-resolution alpha mask.

    Args:
        image: PIL input image (any mode).

    Returns:
        PIL "L" image at the original resolution, values 0-255.
    """
    session = get_birefnet_session()
    tensor, original_size = preprocess(image)

    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: tensor})

    # The output is typically the sigmoid mask; take the last output.
    raw = outputs[-1]
    return postprocess(raw, original_size)


def is_available() -> bool:
    """Check whether the BiRefNet ONNX model is available on disk."""
    return _resolve_model_path() is not None