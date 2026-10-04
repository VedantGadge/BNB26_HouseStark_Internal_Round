"""Worker-callable source ingestion that uses temporary local files only."""

from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy.orm import Session

from app.features.assets.models import Asset
from app.features.assets.schemas import AssetProcessingStatus
from app.features.assets.storage import CloudinaryStorage
from app.features.footage_analysis.probe import MediaProbe, probe_media


class AssetIngestionError(RuntimeError):
    pass


def ingest_uploaded_asset(
    session: Session, *, asset: Asset, storage: CloudinaryStorage
) -> MediaProbe:
    if asset.processing_status != AssetProcessingStatus.UPLOADED.value:
        raise AssetIngestionError("Only verified uploaded assets can be ingested.")
    if asset.format is None:
        raise AssetIngestionError("The uploaded asset has no provider format to download.")
    asset.processing_status = AssetProcessingStatus.PROCESSING.value
    asset.processing_error = None
    session.commit()
    try:
        with TemporaryDirectory(prefix=f"creatorai-asset-{asset.id}-") as temporary_directory:
            source_path = Path(temporary_directory) / f"source.{asset.format}"
            storage.download_original_to_path(
                public_id=asset.public_id,
                resource_type=asset.resource_type,
                asset_format=asset.format,
                destination=source_path,
            )
            probe = probe_media(source_path)
    except Exception as error:
        asset.processing_status = AssetProcessingStatus.FAILED.value
        asset.processing_error = str(error)[:1_000]
        session.commit()
        raise AssetIngestionError("Asset ingestion failed.") from error
    asset.duration_ms = probe.duration_ms
    asset.width = probe.width
    asset.height = probe.height
    asset.processing_status = AssetProcessingStatus.READY.value
    session.commit()
    session.refresh(asset)
    return probe
