from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    api_prefix: str = "/v1"
    cors_origins: str = "http://localhost:3000"
    worker_poll_interval_seconds: float = Field(default=3, gt=0)

    database_url: str | None = None
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_transcription_model: str = "whisper-large-v3-turbo"
    groq_vision_model: str = "qwen/qwen3.8-27b"
    groq_vision_sample_interval_seconds: int = Field(default=30, ge=5, le=300)
    # Two 720p frames stay within Groq's entry-tier input-token limit. Raise this
    # per environment when the account's vision throughput permits it.
    groq_vision_max_frames: int = Field(default=2, ge=1, le=20)
    development_owner_id: str = "local-creator"
    auth_jwks_url: str | None = None
    auth_audience: str | None = None
    auth_issuer: str | None = None

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str | None:
        """Use Psycopg 3 for Neon URLs copied from its dashboard."""

        if self.database_url is None:
            return None
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
