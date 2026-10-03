"""Compatibility import; Person B asset code lives in app.features.assets."""

from app.features.assets.router import (  # noqa: F401
    get_storage,
    project_router,
    router,
)
