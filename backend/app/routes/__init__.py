from fastapi import APIRouter

from app.features.script_creation import router as script_router
from app.features.script_creation import style_router
from app.routes import assets, clips, insights, jobs, projects, publications

api_router = APIRouter()
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(
    script_router.router,
    prefix="/projects/{project_id}/scripts",
    tags=["scripts"],
)
api_router.include_router(style_router.router, prefix="/me/style-profile", tags=["creator-style"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(clips.router, prefix="/clips", tags=["clips"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(publications.router, prefix="/publications", tags=["publications"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
