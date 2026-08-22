from fastapi import APIRouter
from job_radar.api.v1 import health, stream, runs, boards, jobs, settings

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health & Readiness"])
api_router.include_router(stream.router, tags=["Live Updates SSE"])
api_router.include_router(runs.router, tags=["Pipeline Runs"])
api_router.include_router(boards.router, tags=["Job Boards"])
api_router.include_router(jobs.router, tags=["Normalized Jobs"])
api_router.include_router(settings.router, tags=["Settings"])
