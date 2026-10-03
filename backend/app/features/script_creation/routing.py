"""Configuration snapshots shared by every queued script operation."""

from fastapi import HTTPException, status

from app.config import Settings


def require_openrouter_configuration(settings: Settings) -> None:
    if settings.openrouter_api_key is None or not settings.openrouter_default_model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Script generation is not configured.",
        )


def routing_snapshot(settings: Settings) -> dict:
    return {
        "default_model": settings.openrouter_default_model,
        "fallback_models": settings.configured_openrouter_models,
        "free_only": settings.openrouter_free_only,
        "require_structured_output": settings.openrouter_require_structured_output,
        "timeout_seconds": settings.openrouter_timeout_seconds,
        "max_output_tokens": settings.openrouter_max_output_tokens,
        "max_calls": settings.openrouter_max_calls_per_operation,
    }
