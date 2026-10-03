"""Run the real CreatorAI asset upload and ingestion path against configured providers.

The script creates an isolated temporary Project, uploads a local MP4 through the
same signed-session API used by clients, verifies completion, downloads the private
source, probes it with FFprobe, reads the analysis API, and removes the temporary
Neon and Cloudinary records in every outcome.
"""

from __future__ import annotations

import argparse
import mimetypes
import sys
from pathlib import Path
from uuid import UUID, uuid4

import cloudinary.uploader
import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_session_factory
from app.features.assets.models import Asset
from app.features.assets.storage import CloudinaryStorage
from app.features.footage_analysis.ingestion import ingest_uploaded_asset
from app.features.footage_analysis.pipeline import analyze_ready_asset, build_groq_providers
from app.main import create_app
from app.models import Project

MAX_UPLOAD_BYTES = 100_000_000


def main() -> int:
    source_path, analyze_with_groq = _parse_arguments()
    settings = get_settings()
    _require_provider_settings(settings)
    owner_id = settings.development_owner_id
    project_id = uuid4()
    asset_id: UUID | None = None
    public_id: str | None = None

    _create_temporary_project(project_id, owner_id)
    print(f"temporary_project_created={project_id}")
    try:
        with TestClient(create_app()) as client:
            upload_session = _create_upload_session(
                client=client,
                project_id=project_id,
                owner_id=owner_id,
                source_path=source_path,
            )
            asset_id = UUID(upload_session["asset_id"])
            public_id = upload_session["public_id"]
            provider_response = _upload_to_cloudinary(upload_session, source_path)
            _complete_upload(
                client=client,
                owner_id=owner_id,
                asset_id=asset_id,
                provider_asset_id=provider_response["asset_id"],
                provider_version=str(provider_response["version"]),
            )
            probe = _ingest_asset(asset_id, settings)
            if analyze_with_groq:
                _analyze_asset_with_groq(asset_id, settings)
            analysis = _read_analysis(client, owner_id, asset_id)
            print("signed_upload=passed")
            print("completion_verification=passed")
            print(
                "ingestion=passed "
                f"duration_ms={probe.duration_ms} resolution={probe.width}x{probe.height} "
                f"video_codec={probe.video_codec} audio_codec={probe.audio_codec}"
            )
            if analyze_with_groq:
                print(
                    "groq_footage_analysis=passed "
                    f"transcript_segments={len(analysis['transcript_segments'])} "
                    f"visual_observations={len(analysis['visual_observations'])}"
                )
            print(f"analysis_api=passed status={analysis['processing_status']}")
            return 0
    finally:
        _cleanup(project_id=project_id, public_id=public_id)


def _parse_arguments() -> tuple[Path, bool]:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Path to a local video under 100 MB")
    parser.add_argument(
        "--analyze-with-groq",
        action="store_true",
        help="Run timestamped Groq transcription and bounded Groq frame analysis after ingestion.",
    )
    arguments = parser.parse_args()
    source_path = arguments.source.resolve()
    if not source_path.is_file():
        parser.error("source must be an existing regular file")
    if source_path.stat().st_size > MAX_UPLOAD_BYTES:
        parser.error("source exceeds the API's 100 MB upload limit")
    if not mimetypes.guess_type(source_path.name)[0] or not source_path.suffix.lower() == ".mp4":
        parser.error("this smoke test currently accepts MP4 sources only")
    return source_path, arguments.analyze_with_groq


def _require_provider_settings(settings: object) -> None:
    for field_name in (
        "cloudinary_cloud_name",
        "cloudinary_api_key",
        "cloudinary_api_secret",
    ):
        if not getattr(settings, field_name):
            raise RuntimeError(f"{field_name.upper()} must be configured")


def _create_temporary_project(project_id: UUID, owner_id: str) -> None:
    with get_session_factory()() as session:
        session.add(
            Project(
                id=project_id,
                owner_id=owner_id,
                name="CreatorAI real media smoke test",
                brief="Temporary project created by the asset ingestion smoke test.",
                target_platforms=["youtube_shorts"],
            )
        )
        session.commit()


def _create_upload_session(
    *, client: TestClient, project_id: UUID, owner_id: str, source_path: Path
) -> dict[str, object]:
    response = client.post(
        f"/v1/projects/{project_id}/assets/upload-session",
        headers={"X-Creator-ID": owner_id},
        json={
            "filename": source_path.name,
            "content_type": "video/mp4",
            "byte_size": source_path.stat().st_size,
            "kind": "video",
            "tags": ["creatorai-test", "real-ingestion"],
        },
    )
    response.raise_for_status()
    return response.json()


def _upload_to_cloudinary(
    upload_session: dict[str, object], source_path: Path
) -> dict[str, object]:
    form_data = {
        "api_key": str(upload_session["api_key"]),
        "timestamp": str(upload_session["timestamp"]),
        "signature": str(upload_session["signature"]),
        "public_id": str(upload_session["public_id"]),
        "type": str(upload_session["delivery_type"]),
        "overwrite": str(upload_session["overwrite"]).lower(),
    }
    with source_path.open("rb") as source_file:
        response = httpx.post(
            str(upload_session["upload_url"]),
            data=form_data,
            files={"file": (source_path.name, source_file, "video/mp4")},
            timeout=300,
        )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise RuntimeError(f"Cloudinary upload rejected the request: {response.text}") from error
    response_data = response.json()
    if not all(response_data.get(key) for key in ("asset_id", "version", "public_id")):
        raise RuntimeError("Cloudinary upload response was missing required asset identity.")
    return response_data


def _complete_upload(
    *,
    client: TestClient,
    owner_id: str,
    asset_id: UUID,
    provider_asset_id: str,
    provider_version: str,
) -> None:
    response = client.post(
        f"/v1/assets/{asset_id}/complete",
        headers={"X-Creator-ID": owner_id},
        json={
            "provider_asset_id": provider_asset_id,
            "provider_version": provider_version,
        },
    )
    response.raise_for_status()


def _ingest_asset(asset_id: UUID, settings: object):
    storage = CloudinaryStorage(
        cloud_name=getattr(settings, "cloudinary_cloud_name"),
        api_key=getattr(settings, "cloudinary_api_key"),
        api_secret=getattr(settings, "cloudinary_api_secret"),
    )
    with get_session_factory()() as session:
        asset = session.get(Asset, asset_id)
        if asset is None:
            raise RuntimeError("Completed asset was not persisted.")
        return ingest_uploaded_asset(session, asset=asset, storage=storage)


def _analyze_asset_with_groq(asset_id: UUID, settings: object) -> None:
    storage = CloudinaryStorage(
        cloud_name=getattr(settings, "cloudinary_cloud_name"),
        api_key=getattr(settings, "cloudinary_api_key"),
        api_secret=getattr(settings, "cloudinary_api_secret"),
    )
    transcription_provider, vision_provider = build_groq_providers(settings)
    with get_session_factory()() as session:
        asset = session.get(Asset, asset_id)
        if asset is None:
            raise RuntimeError("Ingested asset was not persisted.")
        analyze_ready_asset(
            session,
            asset=asset,
            storage=storage,
            transcription_provider=transcription_provider,
            vision_provider=vision_provider,
        )


def _read_analysis(client: TestClient, owner_id: str, asset_id: UUID) -> dict[str, object]:
    response = client.get(
        f"/v1/assets/{asset_id}/analysis", headers={"X-Creator-ID": owner_id}
    )
    response.raise_for_status()
    return response.json()


def _cleanup(*, project_id: UUID, public_id: str | None) -> None:
    cleanup_failures: list[str] = []
    if public_id:
        try:
            cloudinary.uploader.destroy(
                public_id,
                resource_type="video",
                type="authenticated",
                invalidate=True,
            )
        except Exception as error:  # pragma: no cover - only live provider failures
            cleanup_failures.append(f"Cloudinary cleanup failed: {type(error).__name__}")
    try:
        with get_session_factory()() as session:
            project = session.get(Project, project_id)
            if project is not None:
                session.delete(project)
                session.commit()
    except Exception as error:  # pragma: no cover - only live provider failures
        cleanup_failures.append(f"Neon cleanup failed: {type(error).__name__}")
    print("temporary_records_removed=" + ("false" if cleanup_failures else "true"))
    for failure in cleanup_failures:
        print(failure, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
