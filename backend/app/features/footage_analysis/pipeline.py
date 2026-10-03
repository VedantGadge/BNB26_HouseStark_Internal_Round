"""Worker-callable Groq analysis stage that persists source-grounded evidence."""

from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy.orm import Session

from app.features.assets.models import Asset
from app.features.assets.schemas import AssetProcessingStatus
from app.features.assets.storage import CloudinaryStorage
from app.features.footage_analysis.persistence import (
    replace_transcript_segments,
    replace_visual_observations,
)
from app.features.footage_analysis.transcription import TranscriptionProvider
from app.features.footage_analysis.vision import VisionProvider


class FootageAnalysisError(RuntimeError):
    pass


def analyze_ready_asset(
    session: Session,
    *,
    asset: Asset,
    storage: CloudinaryStorage,
    transcription_provider: TranscriptionProvider,
    vision_provider: VisionProvider,
) -> None:
    """Run provider analysis on an already-ingested video; safe for Person A's job worker."""

    if asset.processing_status != AssetProcessingStatus.READY.value:
        raise FootageAnalysisError("Only ready assets can be analyzed.")
    if asset.format is None:
        raise FootageAnalysisError("The ready asset has no source format.")
    asset.processing_status = AssetProcessingStatus.PROCESSING.value
    asset.processing_error = None
    session.commit()
    try:
        with TemporaryDirectory(prefix=f"creatorai-analysis-{asset.id}-") as temporary_directory:
            source_path = Path(temporary_directory) / f"source.{asset.format}"
            storage.download_original_to_path(
                public_id=asset.public_id,
                resource_type=asset.resource_type,
                asset_format=asset.format,
                destination=source_path,
            )
            transcript_segments = transcription_provider.transcribe(source_path)
            visual_observations = vision_provider.inspect(source_path)
            replace_transcript_segments(session, asset=asset, segments=transcript_segments)
            replace_visual_observations(session, asset=asset, observations=visual_observations)
            asset.processing_status = AssetProcessingStatus.READY.value
            session.commit()
    except Exception as error:
        asset.processing_status = AssetProcessingStatus.FAILED.value
        asset.processing_error = str(error)[:1_000]
        session.commit()
        raise FootageAnalysisError("Footage analysis failed.") from error


def build_groq_providers(settings: object) -> tuple[TranscriptionProvider, VisionProvider]:
    """Construct the configured providers at job-execution time, never at import time."""

    from app.features.footage_analysis.transcription import GroqTranscriptionProvider
    from app.features.footage_analysis.vision import GroqVisionProvider

    api_key = getattr(settings, "groq_api_key")
    if not api_key:
        raise FootageAnalysisError("GROQ_API_KEY must be configured before footage analysis.")
    base_url = getattr(settings, "groq_base_url")
    return (
        GroqTranscriptionProvider(
            api_key=api_key,
            base_url=base_url,
            model=getattr(settings, "groq_transcription_model"),
        ),
        GroqVisionProvider(
            api_key=api_key,
            base_url=base_url,
            model=getattr(settings, "groq_vision_model"),
            interval_seconds=getattr(settings, "groq_vision_sample_interval_seconds"),
            max_frames=getattr(settings, "groq_vision_max_frames"),
        ),
    )
