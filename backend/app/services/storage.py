"""Compatibility imports; asset storage belongs to app.features.assets."""

from app.features.assets.storage import CloudinaryStorage, UploadedAssetReference

__all__ = ["CloudinaryStorage", "UploadedAssetReference"]
