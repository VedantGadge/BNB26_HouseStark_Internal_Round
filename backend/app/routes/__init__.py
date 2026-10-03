from fastapi import APIRouter

from app.features.assets import router as assets
from app.features.clip_generation import router as clip_generation
from app.features.editing import router as editing
from app.features.footage_analysis import router as footage_analysis
from app.features.script_alignment import router as script_alignment
from app.routes import clips, insights, jobs, projects, publications, scripts

api_router = APIRouter()
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(assets.project_router, prefix="/projects", tags=["assets"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(footage_analysis.router, prefix="/assets", tags=["footage-analysis"])
api_router.include_router(script_alignment.router, prefix="/assets", tags=["script-alignment"])
api_router.include_router(clip_generation.router, prefix="/assets", tags=["clip-generation"])
api_router.include_router(editing.candidate_router, prefix="/clip-candidates", tags=["editing"])
api_router.include_router(editing.router, prefix="/edit-versions", tags=["editing"])
api_router.include_router(scripts.router, prefix="/scripts", tags=["scripts"])
api_router.include_router(clips.router, prefix="/clips", tags=["clips"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(publications.router, prefix="/publications", tags=["publications"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
