from fastapi import Header, HTTPException, status

from app.config import get_settings


def get_current_owner_id(x_creator_id: str | None = Header(default=None)) -> str:
    """Temporary development identity seam.

    Person A will replace this dependency with verified JWT/session claims. Keeping the
    boundary here means Person B routes never trust an owner ID in a request body.
    """

    settings = get_settings()
    if settings.environment != "production":
        return x_creator_id or settings.development_owner_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication is not configured for this environment.",
    )
