

import modal


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        "fastapi==0.115.12",
        "python-multipart==0.0.20",
        "pillow==11.2.1",
        "rembg==2.0.65",
        "onnxruntime-gpu==1.21.1",
        "pydantic-settings==2.9.1",
    )

    .run_commands("python -c \"from rembg import new_session; new_session('isnet-general-use')\"")
)

app = modal.App("bg-remover-api", image=image)


@app.function(
    gpu="A10G",
    timeout=60,
    allow_concurrent_inputs=10,
    container_idle_timeout=300,
)
@modal.asgi_app()
def fastapi_app():
    from app.main import app as web_app
    return web_app
