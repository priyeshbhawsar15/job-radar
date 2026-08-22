from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from job_radar.db.session import get_db_session
from job_radar.db.models.candidate import CandidateJob

router = APIRouter(prefix="/jobs", tags=["Normalized Jobs"])

@router.get("", response_model=List[dict])
async def list_jobs(
    board_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    query = select(CandidateJob).order_by(CandidateJob.discovered_at.desc())
    if board_id:
        query = query.where(CandidateJob.board_id == board_id)

    res = await db.execute(query)
    jobs = res.scalars().all()
    out = []
    for j in jobs:
        out.append({
            "candidate_id": j.candidate_id,
            "board_id": j.board_id,
            "title": j.title,
            "company": j.company,
            "company_name": j.company,
            "location": j.location,
            "department": j.department,
            "employment_type": j.employment_type,
            "public_apply_url": j.public_apply_url,
            "description": j.description,
            "salary_raw": j.salary_raw,
            "salary_min": j.salary_min,
            "salary_max": j.salary_max,
            "salary_currency": j.salary_currency,
            "first_seen_at": j.discovered_at.isoformat() if j.discovered_at else None,
            "last_seen_at": j.last_seen_at.isoformat() if j.last_seen_at else None,
            "detail_enrichment_status": j.detail_enrichment_status,
            "detail_enrichment_error_code": j.detail_enrichment_error_code
        })
    return out
