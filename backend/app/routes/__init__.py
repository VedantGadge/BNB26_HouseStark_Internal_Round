from fastapi import APIRouter

from app.features.assets import router as assets
from app.features.clip_generation import router as clip_generation
from app.features.content_workflow import router as workflow_router
from app.features.editing import router as editing
from app.features.footage_analysis import router as footage_analysis
from app.features.media_workflow.insights import router as insights_router
from app.features.media_workflow.router import router as media_router
from app.features.platform_exports import router as platform_exports
from app.features.script_alignment import router as script_alignment
from app.features.script_creation import router as script_router
from app.features.script_creation import style_router
from app.routes import clips, insights, jobs, projects, publications

api_router = APIRouter()
api_router.include_router(media_router, tags=["media-workflow"])
api_router.include_router(insights_router, tags=["insights"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(workflow_router.router, prefix="/projects", tags=["content-workflow"])
api_router.include_router(
    script_router.router,
    prefix="/projects/{project_id}/scripts",
    tags=["scripts"],
)
api_router.include_router(style_router.router, prefix="/me/style-profile", tags=["creator-style"])
api_router.include_router(assets.project_router, prefix="/projects", tags=["assets"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(footage_analysis.router, prefix="/assets", tags=["footage-analysis"])
api_router.include_router(script_alignment.router, prefix="/assets", tags=["script-alignment"])
api_router.include_router(clip_generation.router, prefix="/assets", tags=["clip-generation"])
api_router.include_router(editing.candidate_router, prefix="/clip-candidates", tags=["editing"])
api_router.include_router(editing.router, prefix="/edit-versions", tags=["editing"])
api_router.include_router(
    platform_exports.version_router, prefix="/edit-versions", tags=["platform-exports"]
)
api_router.include_router(
    platform_exports.router, prefix="/platform-exports", tags=["platform-exports"]
)
api_router.include_router(clips.router, prefix="/clips", tags=["clips"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(publications.router, prefix="/publications", tags=["publications"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
