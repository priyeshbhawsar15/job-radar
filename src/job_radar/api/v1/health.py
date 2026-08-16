from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from job_radar.db.session import get_db_session
from job_radar.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Liveness check returning basic service info."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db_session)):
    """Readiness check checking database availability."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_530_SERVICE_UNAVAILABLE,
            detail=f"Database readiness check failed: {str(e)}"
        )

    return {
        "status": "ready",
        "service": settings.PROJECT_NAME,
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
