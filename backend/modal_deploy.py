

import modal


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1-mesa-glx", "libglib2.0-0", "libgomp1")
    .pip_install(
        "fastapi==0.115.12",
        "python-multipart==0.0.20",
        "pillow==11.2.1",
        "numpy>=1.26,<2.0",
        "onnxruntime-gpu==1.21.1",
        "pydantic-settings==2.9.1",
        "scipy>=1.13.0",
        "rembg==2.0.65",
        "opencv-python-headless>=4.10.0",
    )
    # Pre-download rembg fallback model.
    .run_commands("python -c \"from rembg import new_session; new_session('isnet-general-use')\" || true")
)

app = modal.App("bg-remover-api", image=image)

# Volume for BiRefNet / ViTMatte ONNX models (mount at runtime).
model_volume = modal.Volume.from_name("birefnet-models", create_if_missing=True)


@app.function(
    gpu="A10G",
    timeout=120,
    allow_concurrent_inputs=10,
    container_idle_timeout=300,
    volumes={"/models": model_volume},
    environment={
        "BG_REMOVER_BIREFNET_ONNX_PATH": "/models/birefnet.onnx",
        "BG_REMOVER_VITMATTE_ONNX_PATH": "/models/vitmatte.onnx",
        "BG_REMOVER_USE_VITMATTE": "true",
    },
)
@modal.asgi_app()
def fastapi_app():
    from app.main import app as web_app
    return web_app
