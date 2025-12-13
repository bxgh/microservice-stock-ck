from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

from services.stock_pool.blacklist_service import blacklist_service

router = APIRouter(prefix="/api/v1/blacklist", tags=["stock-pool"])

class BlacklistAddRequest(BaseModel):
    code: str
    reason: str
    reason_type: str  # tech_stop, fundamental, regulatory, permanent
    loss_amount: Optional[float] = None

class BlacklistCheckRequest(BaseModel):
    codes: List[str]

class BlacklistResponse(BaseModel):
    code: str
    is_blacklisted: bool
    reason: Optional[str] = None
    release_date: Optional[date] = None

class BatchCheckResponse(BaseModel):
    results: List[BlacklistResponse]

@router.post("", response_model=BlacklistResponse)
async def add_to_blacklist(request: BlacklistAddRequest):
    """手动添加黑名单"""
    entry = await blacklist_service.add_to_blacklist(
        code=request.code,
        reason=request.reason,
        reason_type=request.reason_type,
        loss_amount=request.loss_amount
    )
    return BlacklistResponse(
        code=entry.code,
        is_blacklisted=True,
        reason=entry.reason,
        release_date=entry.release_date
    )

@router.post("/check", response_model=BatchCheckResponse)
async def check_blacklist(request: BlacklistCheckRequest):
    """批量检查黑名单"""
    results_map = await blacklist_service.batch_check(request.codes)
    response_list = []
    for code in request.codes:
        data = results_map.get(code, {"is_blacklisted": False})
        response_list.append(BlacklistResponse(
            code=code,
            is_blacklisted=data.get("is_blacklisted", False),
            reason=data.get("reason"),
            release_date=data.get("release_date")
        ))
    return BatchCheckResponse(results=response_list)

@router.post("/cleanup")
async def cleanup_expired():
    """手动触发过期清理"""
    count = await blacklist_service.clean_expired_blacklist()
    return {"status": "success", "cleaned_count": count}
