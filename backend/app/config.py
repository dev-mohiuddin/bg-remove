

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    


    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


    model_name: str = "isnet-general-use"


    max_file_size_mb: int = 20


    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_prefix": "BG_REMOVER_"}


settings = Settings()
