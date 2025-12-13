from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

from services.stock_pool.candidate_service import candidate_service

router = APIRouter(prefix="/api/v1/candidates", tags=["stock-pool"])

class CandidateResponse(BaseModel):
    code: str
    pool_type: str
    sub_pool: Optional[str]
    score: float
    rank: int
    entry_date: date
    entry_reason: Optional[str]

class RefreshResponse(BaseModel):
    status: str
    pool_type: str
    count: int

@router.post("/refresh", response_model=RefreshResponse)
async def refresh_pool(pool_type: str = Query(..., regex="^(long|swing)$")):
    """
    手动刷新候选池
    pool_type: 'long' or 'swing'
    """
    count = await candidate_service.refresh_pool(pool_type)
    return RefreshResponse(
        status="success",
        pool_type=pool_type,
        count=count
    )

@router.get("/{pool_type}", response_model=List[CandidateResponse])
async def get_candidates(
    pool_type: str,
    sub_pool: Optional[str] = None,
    limit: int = 100
):
    """
    查询候选池
    """
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
