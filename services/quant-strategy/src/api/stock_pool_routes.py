"""
Stock Pool API Routes

Provides endpoints for:
- Querying Universe Pool
- Managing filter configuration
- Triggering pool refresh (for task-scheduler)
"""
import logging
from typing import Optional, List
from datetime import datetime
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.stock_pool.universe_pool_service import universe_pool_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pools", tags=["Stock Pools"])


# ========================
# Request/Response Models
# ========================

class FilterConfigResponse(BaseModel):
    """筛选配置响应"""
    config_name: str
    min_list_months: int
    min_avg_turnover: float
    min_market_cap: float
    min_turnover_ratio: float
    is_active: bool
    updated_at: Optional[datetime] = None


class FilterConfigUpdateRequest(BaseModel):
    """筛选配置更新请求"""
    min_list_months: Optional[int] = Field(None, ge=1, le=120, description="最小上市月份")
    min_avg_turnover: Optional[float] = Field(None, ge=0, description="最小日均成交额(万元)")
    min_market_cap: Optional[float] = Field(None, ge=0, description="最小市值(亿元)")
    min_turnover_ratio: Optional[float] = Field(None, ge=0, le=100, description="最小换手率(%)")


class RefreshRequest(BaseModel):
    """刷新请求 (供 task-scheduler 调用)"""
    triggered_by: str = Field("manual", description="触发来源")
    job_id: Optional[str] = Field(None, description="调度任务ID")


class RefreshResponse(BaseModel):
    """刷新响应"""
    success: bool
    total_stocks: int
    qualified_count: int
    disqualified_count: int
    new_entries: int
    removed_entries: int
    duration_seconds: float
    message: str


class StockItem(BaseModel):
    """股票项"""
    code: str
    name: str
    exchange: Optional[str] = None
    market_cap: Optional[float] = None
    avg_turnover_20d: Optional[float] = None
    turnover_ratio_20d: Optional[float] = None


class UniversePoolResponse(BaseModel):
    """Universe Pool 响应"""
    success: bool
    total: int
    stocks: List[StockItem]


class PoolStatsResponse(BaseModel):
    """池统计响应"""
    success: bool
    total_qualified: int
    total_disqualified: int
    by_exchange: dict
    avg_market_cap: float
    avg_turnover: float
    last_refresh: Optional[datetime] = None


# ========================
# API Endpoints
# ========================

@router.get("/universe", response_model=UniversePoolResponse)
async def get_universe_pool(
    limit: int = Query(1000, ge=1, le=5000, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    获取 Universe Pool 股票列表
    
    返回通过筛选的合格股票。
    """
    try:
        await universe_pool_service.initialize()
        stocks = await universe_pool_service.get_qualified_stocks(limit=limit, offset=offset)
        
        stock_items = [
            StockItem(
                code=s.code,
                name=s.name,
                exchange=s.exchange,
                market_cap=s.market_cap,
                avg_turnover_20d=s.avg_turnover_20d,
                turnover_ratio_20d=s.turnover_ratio_20d
            )
            for s in stocks
        ]
        
        return UniversePoolResponse(
            success=True,
            total=len(stock_items),
            stocks=stock_items
        )
    except Exception as e:
        logger.error(f"Failed to get universe pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/universe/stats", response_model=PoolStatsResponse)
async def get_universe_stats():
    """
    获取 Universe Pool 统计信息
    
    返回合格/不合格数量、按交易所分布、平均市值等。
    """
    try:
        await universe_pool_service.initialize()
        stats = await universe_pool_service.get_pool_stats()
        
        return PoolStatsResponse(
            success=True,
            total_qualified=stats.total_qualified,
            total_disqualified=stats.total_disqualified,
            by_exchange=stats.by_exchange,
            avg_market_cap=stats.avg_market_cap,
            avg_turnover=stats.avg_turnover,
            last_refresh=stats.last_refresh
        )
    except Exception as e:
        logger.error(f"Failed to get universe stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/universe/refresh", response_model=RefreshResponse)
async def refresh_universe_pool(request: RefreshRequest = None):
    """
    刷新 Universe Pool
    
    由 task-scheduler 微服务调用，或手动触发。
    
    **task-scheduler 配置示例**:
    ```yaml
    jobs:
      - name: refresh_universe_pool
        cron: "0 22 * * 0"  # 每周日 22:00
        target:
          service: quant-strategy
          endpoint: /api/v1/pools/universe/refresh
          method: POST
    ```
    """
    if request is None:
        request = RefreshRequest()
    
    try:
        await universe_pool_service.initialize()
        result = await universe_pool_service.refresh_universe_pool(
            triggered_by=request.triggered_by,
            job_id=request.job_id
        )
        
        return RefreshResponse(**asdict(result))
    except Exception as e:
        logger.error(f"Failed to refresh universe pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/universe/config", response_model=FilterConfigResponse)
async def get_filter_config():
    """
    获取当前筛选配置
    
    返回活跃的筛选参数配置。
    """
    try:
        await universe_pool_service.initialize()
        config = await universe_pool_service.get_active_config()
        
        return FilterConfigResponse(
            config_name=config.config_name,
            min_list_months=config.min_list_months,
            min_avg_turnover=config.min_avg_turnover,
            min_market_cap=config.min_market_cap,
            min_turnover_ratio=config.min_turnover_ratio,
            is_active=config.is_active,
            updated_at=config.updated_at
        )
    except Exception as e:
        logger.error(f"Failed to get filter config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/universe/config", response_model=FilterConfigResponse)
async def update_filter_config(request: FilterConfigUpdateRequest):
    """
    更新筛选配置
    
    动态调整筛选参数，无需重新部署。
    修改后需手动触发刷新才能生效。
    """
    try:
        await universe_pool_service.initialize()
        config = await universe_pool_service.update_filter_config(
            min_list_months=request.min_list_months,
            min_avg_turnover=request.min_avg_turnover,
            min_market_cap=request.min_market_cap,
            min_turnover_ratio=request.min_turnover_ratio
        )
        
        return FilterConfigResponse(
            config_name=config.config_name,
            min_list_months=config.min_list_months,
            min_avg_turnover=config.min_avg_turnover,
            min_market_cap=config.min_market_cap,
            min_turnover_ratio=config.min_turnover_ratio,
            is_active=config.is_active,
            updated_at=config.updated_at
        )
    except Exception as e:
        logger.error(f"Failed to update filter config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/universe/config/reset", response_model=FilterConfigResponse)
async def reset_filter_config():
    """
    重置筛选配置为默认值
    
    恢复默认参数:
    - min_list_months: 12
    - min_avg_turnover: 3000万
    - min_market_cap: 30亿
    - min_turnover_ratio: 0.3%
    """
    try:
        await universe_pool_service.initialize()
        config = await universe_pool_service.update_filter_config(
            min_list_months=12,
            min_avg_turnover=3000.0,
            min_market_cap=30.0,
            min_turnover_ratio=0.3
        )
        
        return FilterConfigResponse(
            config_name=config.config_name,
            min_list_months=config.min_list_months,
            min_avg_turnover=config.min_avg_turnover,
            min_market_cap=config.min_market_cap,
            min_turnover_ratio=config.min_turnover_ratio,
            is_active=config.is_active,
            updated_at=config.updated_at
        )
    except Exception as e:
        logger.error(f"Failed to reset filter config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
