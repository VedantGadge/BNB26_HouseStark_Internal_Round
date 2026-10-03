"""Durable media operations; immutable snapshots and artifacts survive retries."""

from uuid import UUID

from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.features.assets.access import get_owned_asset
from app.features.assets.storage import CloudinaryStorage
from app.features.clip_generation.service import generate_candidates
from app.features.editing.models import EditRender, EditVersion
from app.features.editing.render_service import render_edit_version
from app.features.editing.schemas import EditRecipePayload, EditVersionCreate
from app.features.editing.service import create_edit_version, get_owned_edit_version
from app.features.footage_analysis.ingestion import ingest_uploaded_asset
from app.features.footage_analysis.models import TranscriptSegment, VisualObservation
from app.features.footage_analysis.pipeline import analyze_ready_asset, build_groq_providers
from app.features.script_alignment.semantic import semantic_matches
from app.features.script_alignment.service import replace_alignments
from app.features.script_creation.provider import OpenRouterProvider
from app.features.script_creation.routing import routing_snapshot
from app.graphs.repurpose import build_repurpose_graph
from app.models import Job, LlmCall, ScriptVersion
from app.schemas import JobType

PRESETS = {"vertical": (1080, 1920), "square": (1080, 1080), "landscape": (1920, 1080)}


class MediaWorkflowService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        storage: CloudinaryStorage,
        checkpointer=None,
        providers=None,
        alignment_provider=None,
    ):
        self.session, self.settings, self.storage = session, settings, storage
        self.checkpointer, self.providers = checkpointer, providers
        self.alignment_provider = alignment_provider

    def stage(self, job, stage):
        job.stage = stage
        self.session.commit()

    def execute(self, job: Job):
        try:
            if job.type == JobType.ASSET_INGESTION:
                self.ingest(job)
                self.complete(job)
            elif job.type == JobType.CLIP_GENERATION:
                self.clips(job)
            elif job.type == JobType.MEDIA_EXPORT:
                self.export(job)
                self.complete(job)
            else:
                raise ValueError("Unsupported media job type")
        except Exception as error:
            self.session.rollback()
            if job.type == JobType.ASSET_INGESTION:
                asset = get_owned_asset(
                    self.session, UUID(job.input_snapshot["asset_id"]), job.owner_id
                )
                asset.processing_status, asset.processing_error = "failed", str(error)[:1000]
            job.status, job.stage, job.error = "failed", "failed", str(error)[:1000]
            job.lease_expires_at = None
            self.session.commit()

    def complete(self, job):
        job.status, job.stage, job.error = "completed", "completed", None
        job.lease_expires_at = None
        self.session.commit()

    def ingest(self, job):
        asset = get_owned_asset(self.session, UUID(job.input_snapshot["asset_id"]), job.owner_id)
        self.stage(job, "probing_source")
        if asset.processing_status != "ready":
            asset.processing_status = "uploaded"
            self.session.commit()
            ingest_uploaded_asset(self.session, asset=asset, storage=self.storage)
        if asset.kind == "video":
            self.stage(job, "transcribing_and_inspecting_frames")
            transcriber, vision = self.providers or build_groq_providers(self.settings)
            analyze_ready_asset(
                self.session,
                asset=asset,
                storage=self.storage,
                transcription_provider=transcriber,
                vision_provider=vision,
            )
        elif asset.kind == "audio":
            self.stage(job, "transcribing_audio")
            transcriber, _ = self.providers or build_groq_providers(self.settings)
            from pathlib import Path
            from tempfile import TemporaryDirectory

            from app.features.footage_analysis.persistence import replace_transcript_segments

            with TemporaryDirectory(prefix="creatorai-audio-") as directory:
                path = Path(directory) / f"source.{asset.format}"
                self.storage.download_original_to_path(
                    public_id=asset.public_id,
                    resource_type=asset.resource_type,
                    asset_format=asset.format,
                    destination=path,
                )
                replace_transcript_segments(
                    self.session, asset=asset, segments=transcriber.transcribe(path)
                )
                self.session.commit()
        job.input_snapshot = {**job.input_snapshot, "result": {"asset_id": str(asset.id)}}

    def propose(self, job, state):
        # The application snapshot is a second idempotency boundary if a checkpoint write fails.
        if job.input_snapshot.get("result"):
            return {**state, **job.input_snapshot["result"]}
        asset = get_owned_asset(self.session, UUID(state["asset_id"]), job.owner_id)
        script = self.session.get(ScriptVersion, UUID(state["script_version_id"]))
        if script is None or script.project_id != asset.project_id:
            raise ValueError("The selected script no longer belongs to this project")
        self.stage(job, "aligning_script_and_visual_evidence")
        transcript = list(
            self.session.scalars(
                select(TranscriptSegment).where(TranscriptSegment.asset_id == asset.id)
            )
        )
        visuals = list(
            self.session.scalars(
                select(VisualObservation).where(VisualObservation.asset_id == asset.id)
            )
        )
        routing = job.routing_snapshot or routing_snapshot(self.settings)
        matches, call = semantic_matches(
            sections=script.content["sections"],
            transcript_segments=transcript,
            visual_observations=visuals,
            provider=self.alignment_provider or OpenRouterProvider(self.settings),
            routing=routing,
        )
        self.session.add(
            LlmCall(
                job_id=job.id,
                attempt=job.attempt,
                requested_model=routing["default_model"] or "fixture",
                actual_model=call.actual_model,
                provider=call.provider,
                input_tokens=call.input_tokens,
                output_tokens=call.output_tokens,
                outcome="success",
            )
        )
        alignments = replace_alignments(
            self.session,
            asset=asset,
            script_text="",
            transcript_segments=transcript,
            visual_observations=visuals,
            script_version_id=script.id,
            sections=script.content["sections"],
            semantic_matches=matches,
        )
        self.stage(job, "ranking_grounded_clips")
        candidates = generate_candidates(
            self.session,
            asset=asset,
            alignments=alignments,
            max_candidates=state["max_candidates"],
            min_duration_ms=8000,
            max_duration_ms=60000,
        )
        if not candidates:
            raise ValueError("No usable grounded clips. Select a source range manually.")
        versions = []
        for candidate in candidates:
            version = self.session.scalar(
                select(EditVersion)
                .where(EditVersion.candidate_id == candidate.id)
                .order_by(EditVersion.revision.desc())
            )
            versions.append(
                version
                or create_edit_version(
                    self.session, candidate=candidate, asset=asset, payload=EditVersionCreate()
                )
            )
        self.stage(job, "rendering_draft_preview")
        preview = render_edit_version(
            self.session,
            version=versions[0],
            asset=asset,
            storage=self.storage,
            settings=self.settings,
            job_id=job.id,
        )
        result = {
            "candidate_ids": [str(c.id) for c in candidates],
            "edit_version_ids": [str(v.id) for v in versions],
            "preview_render_id": str(preview.id),
        }
        job.input_snapshot = {**job.input_snapshot, "result": result}
        self.session.commit()
        return {**state, **result}

    def clips(self, job):
        if self.checkpointer is None:
            raise ValueError("A durable graph checkpointer is required for clip generation")
        job.graph_thread_id = job.graph_thread_id or f"media:{job.id}"
        self.session.commit()
        graph = build_repurpose_graph(lambda state: self.propose(job, state), self.checkpointer)
        config = {"configurable": {"thread_id": job.graph_thread_id}}
        snapshot = graph.get_state(config)
        if job.input_snapshot.get("review"):
            version = get_owned_edit_version(
                self.session, UUID(job.input_snapshot["review"]["edit_version_id"]), job.owner_id
            )
            result = graph.invoke(Command(resume={"edit_version_id": str(version.id)}), config)
        else:
            result = graph.invoke(None if snapshot.values else job.input_snapshot, config)
        if result.get("__interrupt__"):
            job.status, job.stage = "waiting_review", "creator_review"
            job.lease_expires_at = None
            self.session.commit()
        else:
            job.input_snapshot = {
                **job.input_snapshot,
                "result": {
                    **job.input_snapshot.get("result", {}),
                    "selected_edit_version_id": result["selected_edit_version_id"],
                },
            }
            self.complete(job)

    def export(self, job):
        payload = job.input_snapshot
        version = get_owned_edit_version(
            self.session, UUID(payload["edit_version_id"]), job.owner_id
        )
        asset = get_owned_asset(self.session, version.asset_id, job.owner_id)
        recipe = EditRecipePayload.model_validate(version.recipe)
        width, height = PRESETS[payload["preset"]]
        recipe.output.width, recipe.output.height, recipe.output.fit = width, height, payload["fit"]
        self.stage(job, "rendering_and_verifying_export")
        render = render_edit_version(
            self.session,
            version=version,
            asset=asset,
            storage=self.storage,
            settings=self.settings,
            job_id=job.id,
            preset_name=payload["preset"],
            platform=payload["platform"],
            supporting_copy={k: payload[k] for k in ("title", "caption", "hashtags")},
            recipe_override=recipe,
        )
        job.input_snapshot = {**payload, "result": {"export_id": str(render.id)}}


def owned_render(session, owner_id, render_id):
    from fastapi import HTTPException

    from app.features.assets.models import Asset

    render = session.scalar(
        select(EditRender).join(Asset).where(EditRender.id == render_id, Asset.owner_id == owner_id)
    )
    if render is None:
        raise HTTPException(404, "Export not found.")
    return render
