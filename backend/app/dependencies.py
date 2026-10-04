from fastapi import Depends

from app.auth import AuthenticatedCreator, get_current_creator


def get_current_owner_id(creator: AuthenticatedCreator = Depends(get_current_creator)) -> str:
    """Use the same verified creator for scripts, assets, edits, and exports."""
    return creator.id
