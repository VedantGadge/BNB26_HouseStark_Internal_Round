"""Compatibility imports; source ingestion belongs to the footage-analysis feature."""

from app.features.footage_analysis.ingestion import AssetIngestionError, ingest_uploaded_asset

__all__ = ["AssetIngestionError", "ingest_uploaded_asset"]
