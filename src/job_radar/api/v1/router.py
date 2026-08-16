from fastapi import APIRouter
from job_radar.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health & Readiness"])
