"""
策略管理API路由 - 量化策略服务
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import asyncio

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from models.base_models import ApiResponse
from models.strategy_models import (
    Strategy, 
    StrategyCreate, 
    StrategyType,
    BacktestRequest,
    BacktestResult,
    Signal,
)
from core.manager import BackgroundTaskManager

logger = logging.getLogger(__name__)

# 创建路由器
strategy_router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])

# 模拟策略存储 (后续替换为数据库)
_strategies: Dict[str, Strategy] = {}

class JobRunRequest(BaseModel):
    """任务运行请求"""
    job_type: str  # backtest, signal_generation, etc.
    params: Dict[str, Any] = {}

@strategy_router.get("/", response_model=None, summary="获取策略列表")
async def list_strategies(
    strategy_type: Optional[StrategyType] = None,
    enabled: Optional[bool] = None
) -> ApiResponse:
    """获取所有策略列表"""
    try:
        strategies = list(_strategies.values())
        if strategy_type:
            strategies = [s for s in strategies if s.strategy_type == strategy_type]
        if enabled is not None:
            strategies = [s for s in strategies if s.enabled == enabled]
        
        return ApiResponse(
            success=True,
            message=f"获取到 {len(strategies)} 个策略",
            data={
                "total": len(strategies),
                "strategies": [s.model_dump() for s in strategies]
            }
        )
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        return ApiResponse(success=False, message=str(e))

@strategy_router.get("/{strategy_id}", response_model=None, summary="获取策略详情")
async def get_strategy(strategy_id: str) -> ApiResponse:
    """获取单个策略详"""
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="策略不存在")
    return ApiResponse(success=True, data=_strategies[strategy_id].model_dump())

@strategy_router.post("/", response_model=None, summary="创建策略")
async def create_strategy(request: StrategyCreate) -> ApiResponse:
    """创建新策略"""
    try:
        strategy_id = f"{request.strategy_type.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        strategy = Strategy(
            id=strategy_id,
            name=request.name,
            strategy_type=request.strategy_type,
            description=request.description,
            parameters=request.parameters,
            stock_pool=request.stock_pool,
            enabled=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        _strategies[strategy_id] = strategy
        return ApiResponse(success=True, message="策略创建成功", data=strategy.model_dump())
    except Exception as e:
        logger.error(f"创建策略失败: {e}")
        return ApiResponse(success=False, message=str(e))

@strategy_router.post("/{strategy_id}/jobs/run", summary="触发策略任务")
async def run_strategy_job(
    strategy_id: str, 
    request: JobRunRequest,
    background_tasks: BackgroundTasks
) -> ApiResponse:
    """
    触发策略任务 (供调度器调用)
    
    - **job_type**: 任务类型 (如 daily_backtest, monitor)
    """
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="Strategy not found")
        
    logger.info(f"Received job trigger for {strategy_id}: {request.job_type}")
    
    # 模拟异步任务执行
    # 在实际实现中，这里会调用 StrategyRegistry 获取策略实例并执行相应方法
    task_id = f"job_{strategy_id}_{datetime.now().timestamp()}"
    
    async def _run_job():
        logger.info(f"Starting job {task_id}...")
        await asyncio.sleep(2) # Mock execution
        logger.info(f"Job {task_id} completed")
    
    # 使用 BackgroundTaskManager 统一管理
    manager = BackgroundTaskManager()
    # 注意：FastAPI的BackgroundTasks在响应后执行，这里我们也利用内部管理器来追踪状态
    # 但为了简单响应，我们可以直接启动
    await manager.start_task(task_id, _run_job())
    
    return ApiResponse(
        success=True,
        message="Task started",
        data={"task_id": task_id, "status": "submitted"}
    )
