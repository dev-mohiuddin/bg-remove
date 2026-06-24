"""
Download and prepare BiRefNet + ViTMatte ONNX models.

Usage:
    python download_models.py

This script downloads the BiRefNet ONNX export from HuggingFace and
optionally the ViTMatte ONNX. If an ONNX export is not available, it
exports the PyTorch checkpoint to ONNX automatically (requires torch).

Models:
    BiRefNet  — https://huggingface.co/ZhengPeng7/BiRefNet
    ViTMatte  — https://huggingface.co/hustvl/ViTMatte-base-distinctions
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(exist_ok=True)


def download_birefnet():
    """Download or export BiRefNet to ONNX."""
    target = MODELS_DIR / "birefnet.onnx"
    if target.exists():
        print(f"[BiRefNet] Already exists: {target} ({target.stat().st_size // 1024 // 1024} MB)")
        return

    print("[BiRefNet] Attempting to download ONNX export from HuggingFace...")
    try:
        from huggingface_hub import hf_hub_download
        # Try known ONNX export repos.
        for repo_id, filename in [
            ("ZhengPeng7/BiRefNet", "onnx/birefnet.onnx"),
            ("ZhengPeng7/BiRefNet", "birefnet.onnx"),
            ("briaai/BRIA-RMBG-2.0", "model.onnx"),  # alternative SOTA
        ]:
            try:
                print(f"  Trying {repo_id}:{filename} ...")
                path = hf_hub_download(repo_id=repo_id, filename=filename)
                import shutil
                shutil.copy2(path, target)
                print(f"  Downloaded to {target}")
                return
            except Exception as exc:
                print(f"  Not available: {exc}")
                continue
    except ImportError:
        print("  huggingface_hub not installed. Install with: pip install huggingface_hub")

    print("[BiRefNet] No pre-built ONNX found. Attempting PyTorch -> ONNX export...")
    try:
        export_birefnet_onnx(target)
    except Exception as exc:
        print(f"  Export failed: {exc}")
        print("\n[FALLBACK] The system will use rembg IS-Net until BiRefNet ONNX is available.")
        print("To enable BiRefNet, manually place the ONNX file at:")
        print(f"  {target}")
        print("Or set the BG_REMOVER_BIREFNET_ONNX_PATH env var.")


def export_birefnet_onnx(target: Path):
    """Export BiRefNet from PyTorch checkpoint to ONNX."""
    import torch
    from huggingface_hub import snapshot_download

    print("  Downloading PyTorch checkpoint...")
    model_dir = snapshot_download(repo_id="ZhengPeng7/BiRefNet")

    # Load the model.
    sys.path.insert(0, model_dir)
    try:
        from models.birefnet import BiRefNet
        from transformers import AutoModelForImageSegmentation
        model = AutoModelForImageSegmentation.from_pretrained(
            model_dir, trust_remote_code=True
        )
    except Exception:
        # Direct weight loading.
        from transformers import AutoModelForImageSegmentation
        model = AutoModelForImageSegmentation.from_pretrained(
            "ZhengPeng7/BiRefNet", trust_remote_code=True
        )

    model.eval()
    model.cuda() if torch.cuda.is_available() else model.cpu()

    dummy = torch.randn(1, 3, 1024, 1024)
    if torch.cuda.is_available():
        dummy = dummy.cuda()

    print("  Exporting to ONNX (this may take a few minutes)...")
    torch.onnx.export(
        model,
        dummy,
        str(target),
        opset_version=17,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
        do_constant_folding=True,
    )
    print(f"  Exported to {target}")


def download_vitmatte():
    """Download or export ViTMatte to ONNX."""
    target = MODELS_DIR / "vitmatte.onnx"
    if target.exists():
        print(f"[ViTMatte] Already exists: {target} ({target.stat().st_size // 1024 // 1024} MB)")
        return

    print("[ViTMatte] ViTMatte ONNX export is not publicly available.")
    print("  The system will use closed-form / guided-filter matting as fallback.")
    print("  To enable ViTMatte, export it manually and place at:")
    print(f"    {target}")
    print("  Or set BG_REMOVER_VITMATTE_ONNX_PATH.")


if __name__ == "__main__":
    print("=" * 60)
    print("  Model Download / Export Utility")
    print("=" * 60)
    download_birefnet()
    print()
    download_vitmatte()
    print()
    print("Done. Models directory:", MODELS_DIR)