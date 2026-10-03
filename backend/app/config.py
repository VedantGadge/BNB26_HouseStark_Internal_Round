from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
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
    worker_lease_seconds: int = Field(default=120, ge=30, le=900)

    database_url: str | None = None
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    auth_jwks_url: str | None = None
    auth_audience: str | None = None
    auth_issuer: str | None = None
    auth_required: bool = True

    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str | None = None
    openrouter_fallback_models: str = ""
    openrouter_free_only: bool = True
    openrouter_require_structured_output: bool = True
    openrouter_timeout_seconds: float = Field(default=30, gt=0, le=120)
    openrouter_max_output_tokens: int = Field(default=2_000, ge=64, le=16_384)
    openrouter_max_calls_per_operation: int = Field(default=3, ge=2, le=5)
    openrouter_max_fallback_models: int = Field(default=2, ge=0, le=3)

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def configured_openrouter_models(self) -> tuple[str, ...]:
        """Configured fallback IDs in priority order, excluding duplicate entries."""

        models: list[str] = []
        for model in self.openrouter_fallback_models.split(","):
            normalized = model.strip()
            if normalized and normalized not in models:
                models.append(normalized)
        return tuple(models[: self.openrouter_max_fallback_models])


@lru_cache
def get_settings() -> Settings:
    return Settings()
