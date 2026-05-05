from datetime import date

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/candidates", tags=["stock-pool"])

class CandidateResponse(BaseModel):
    code: str
    pool_type: str
    sub_pool: str | None
    score: float
    rank: int
    entry_date: date
    entry_reason: str | None

class RefreshResponse(BaseModel):
    status: str
    pool_type: str
    count: int

@router.post("/refresh", response_model=RefreshResponse)
async def refresh_pool(
    request: Request,
    pool_type: str = Query(..., regex="^(long|swing)$")
):
    """
    手动刷新候选池
    pool_type: 'long' or 'swing'
    """
    candidate_service = request.app.state.candidate_service
    count = await candidate_service.refresh_pool(pool_type)
    return RefreshResponse(
        status="success",
        pool_type=pool_type,
        count=count
    )

@router.get("/{pool_type}", response_model=list[CandidateResponse])
async def get_candidates(
    request: Request,
    pool_type: str,
    sub_pool: str | None = None,
    limit: int = 100
):
    """
    查询候选池
    """
    candidate_service = request.app.state.candidate_service
    candidates = await candidate_service.get_candidates(pool_type, sub_pool, limit)
    return [
        CandidateResponse(
            code=c.code,
            pool_type=c.pool_type,
            sub_pool=c.sub_pool,
            score=c.score,
            rank=c.rank,
            entry_date=c.entry_date,
            entry_reason=c.entry_reason
        )
        for c in candidates
    ]
