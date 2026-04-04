from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    STORAGE_PATH: Path = Path(__file__).resolve().parent.parent / "storage"
    DEFAULT_MODEL: str = "llama3.2:latest"

    model_config = {"env_prefix": "AB_"}


settings = Settings()
