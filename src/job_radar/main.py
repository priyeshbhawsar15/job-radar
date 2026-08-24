import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from job_radar.config import settings
from job_radar.api.v1.router import api_router
from job_radar.db.base import Base
from job_radar.db.session import engine
from job_radar.services.scheduler import scheduler_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables for lightweight SQLite/local test mode
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    scheduler_service.start()
    yield
    scheduler_service.shutdown()
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount static files if static directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
