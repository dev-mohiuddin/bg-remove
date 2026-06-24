from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration. All values overridable via BG_REMOVER_* env vars."""

    # --- Server ---
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    host: str = "0.0.0.0"
    port: int = 8000

    # --- File limits ---
    max_file_size_mb: int = 25  # raised for 4K support

    # --- Segmentation model ---
    # Primary: BiRefNet (SOTA). Fallback: rembg IS-Net.
    model_name: str = "isnet-general-use"  # used only if BiRefNet unavailable
    birefnet_onnx_path: str = ""           # override path to BiRefNet ONNX

    # --- Tiled inference (4K / large image support) ---
    tile_size: int = 1024
    tile_overlap: int = 128

    # --- Alpha matting ---
    use_vitmatte: bool = True              # try ViTMatte ONNX if available
    vitmatte_onnx_path: str = ""
    trimap_erode_radius: int = 6
    trimap_dilate_radius: int = 18

    # --- Task management ---
    task_max_concurrent: int = 3
    task_cleanup_interval_s: int = 300
    task_max_age_s: int = 3600

    model_config = {"env_prefix": "BG_REMOVER_"}


settings = Settings()
