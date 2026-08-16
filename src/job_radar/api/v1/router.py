from fastapi import APIRouter
from job_radar.api.v1 import health, stream

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health & Readiness"])
api_router.include_router(stream.router, tags=["Live Updates SSE"])
