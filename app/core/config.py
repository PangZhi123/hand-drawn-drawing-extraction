from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DRAWING_", extra="ignore")

    app_name: str = "hand-drawn-drawing-extraction"
    data_dir: Path = Path("runtime-data")
    max_file_size_mb: int = 30
    max_file_count: int = 10
    review_confidence: float = 0.70
    ocr_backend: str = "qwen_vl"
    tesseract_cmd: str | None = None
    model_base_url: str = "http://127.0.0.1:8080/v1"
    model_name: str = "qwen3-vl-30b-a3b-thinking"
    model_api_key: str = "local"
    model_timeout_seconds: int = 600
    model_max_tokens: int = 8192

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
