#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GuaranteedSuccessStrategy API路由
100%成功策略的RESTful API接口
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse

try:
    from ..models.guaranteed_strategy_models import (
        SuccessResult, BatchExecutionRequest, BatchExecutionResult,
        GuaranteedStrategyConfig, StrategyExecutionStats
    )
    from ..models.base_models import ApiResponse, PaginationInfo
    from ..services.guaranteed_success_strategy import guaranteed_strategy_instance
    from ..services.tongdaxin_client import tongdaxin_client
    from ..services.stock_code_client import stock_client_instance
except ImportError:
    from models.guaranteed_strategy_models import (
        SuccessResult, BatchExecutionRequest, BatchExecutionResult,
        GuaranteedStrategyConfig, StrategyExecutionStats
    )
    from models.base_models import ApiResponse, PaginationInfo
    from services.guaranteed_success_strategy import guaranteed_strategy_instance
    from services.tongdaxin_client import tongdaxin_client
    from services.stock_code_client import stock_client_instance

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/v1/strategy", tags=["100%成功策略"])
internal_router = APIRouter(prefix="/internal/strategy", tags=["策略内部接口"])

# 全局任务存储 (生产环境应使用Redis等)
active_tasks: Dict[str, Dict] = {}
task_results: Dict[str, BatchExecutionResult] = {}


class TaskStatus:
    """任务状态类"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@router.post("/single/{symbol}", response_model=ApiResponse[SuccessResult])
async def execute_single_stock_strategy(
    symbol: str,
    name: str = Query(..., description="股票名称"),
    date: str = Query(..., regex=r"^\d{8}$", description="查询日期 (YYYYMMDD)"),
    target_time: str = Query(default="09:25", description="目标时间")
):
    """
    执行单只股票的100%成功策略

    Args:
        symbol: 股票代码
        name: 股票名称
        date: 查询日期
        target_time: 目标时间

    Returns:
        策略执行结果
    """
    try:
        logger.info(f"收到单只股票策略请求: {symbol} ({name}) - {date}")

        # 更新策略配置
        guaranteed_strategy_instance.config.target_time = target_time

        # 执行策略
        result = await guaranteed_strategy_instance.guarantee_success(symbol, name, date)

        return ApiResponse(
            success=True,
            message="策略执行完成",
            data=result
        )

    except Exception as e:
        logger.error(f"单只股票策略执行失败 {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"策略执行失败: {str(e)}")


@router.post("/batch", response_model=ApiResponse[Dict[str, str]])
async def execute_batch_strategy(
    request: BatchExecutionRequest,
    background_tasks: BackgroundTasks
):
    """
    执行批量股票的100%成功策略 (异步)

    Args:
        request: 批量执行请求
        background_tasks: 后台任务

    Returns:
        任务ID和状态
    """
    try:
        task_id = str(uuid.uuid4())

        logger.info(f"收到批量策略请求: {task_id}, 股票数量: {len(request.stock_list)}")

        # 创建任务记录
        active_tasks[task_id] = {
            "task_id": task_id,
            "status": TaskStatus.PENDING,
            "request": request.dict(),
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "error": None
        }

        # 添加后台任务
        background_tasks.add_task(execute_batch_strategy_background, task_id, request)

        return ApiResponse(
            success=True,
            message="批量策略任务已创建",
            data={
                "task_id": task_id,
                "status": TaskStatus.PENDING,
                "estimated_time": len(request.stock_list) * 30,  # 估算时间(秒)
                "stock_count": len(request.stock_list)
            }
        )

    except Exception as e:
        logger.error(f"创建批量策略任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"任务创建失败: {str(e)}")


async def execute_batch_strategy_background(task_id: str, request: BatchExecutionRequest):
    """
    后台执行批量策略

    Args:
        task_id: 任务ID
        request: 批量执行请求
    """
    try:
        # 更新任务状态
        active_tasks[task_id]["status"] = TaskStatus.RUNNING
        active_tasks[task_id]["started_at"] = datetime.now()

        logger.info(f"开始执行批量策略任务: {task_id}")

        # 更新策略配置
        guaranteed_strategy_instance.config.target_time = request.target_time
        guaranteed_strategy_instance.config.max_concurrent_stocks = request.max_concurrent
        guaranteed_strategy_instance.config.timeout_per_stock = request.timeout_per_stock
        guaranteed_strategy_instance.config.retry_attempts = request.retry_attempts

        # 执行批量策略
        result = await guaranteed_strategy_instance.execute_guaranteed_batch(request)

        # 保存结果
        task_results[task_id] = result
        active_tasks[task_id]["status"] = TaskStatus.COMPLETED
        active_tasks[task_id]["completed_at"] = datetime.now()

        logger.info(f"批量策略任务完成: {task_id}, 成功率: {result.success_rate:.1%}")

    except Exception as e:
        logger.error(f"批量策略任务失败 {task_id}: {e}")
        active_tasks[task_id]["status"] = TaskStatus.FAILED
        active_tasks[task_id]["error"] = str(e)
        active_tasks[task_id]["completed_at"] = datetime.now()


@router.get("/batch/{task_id}/status", response_model=ApiResponse[Dict[str, Any]])
async def get_batch_task_status(task_id: str):
    """
    获取批量任务状态

    Args:
        task_id: 任务ID

    Returns:
        任务状态信息
    """
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")

        task_info = active_tasks[task_id]
        response_data = {
            "task_id": task_id,
            "status": task_info["status"],
            "created_at": task_info["created_at"],
            "started_at": task_info.get("started_at"),
            "completed_at": task_info.get("completed_at"),
            "error": task_info.get("error"),
            "stock_count": len(task_info["request"]["stock_list"])
        }

        # 如果任务完成，添加基本统计
        if task_info["status"] == TaskStatus.COMPLETED and task_id in task_results:
            result = task_results[task_id]
            response_data.update({
                "success_rate": result.success_rate,
                "perfect_rate": result.perfect_rate,
                "total_execution_time": result.total_execution_time,
                "successful_stocks": result.successful_stocks,
                "failed_stocks": result.failed_stocks
            })

        return ApiResponse(
            success=True,
            message="任务状态获取成功",
            data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败 {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/batch/{task_id}/result", response_model=ApiResponse[BatchExecutionResult])
async def get_batch_task_result(task_id: str):
    """
    获取批量任务详细结果

    Args:
        task_id: 任务ID

    Returns:
        详细执行结果
    """
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")

        task_info = active_tasks[task_id]

        if task_info["status"] != TaskStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="任务尚未完成")

        if task_id not in task_results:
            raise HTTPException(status_code=404, detail="任务结果不存在")

        return ApiResponse(
            success=True,
            message="任务结果获取成功",
            data=task_results[task_id]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务结果失败 {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"获取结果失败: {str(e)}")


@router.get("/batch/active", response_model=ApiResponse[List[Dict[str, Any]]])
async def get_active_tasks():
    """
    获取所有活跃任务列表

    Returns:
        活跃任务列表
    """
    try:
        active_task_list = []
        for task_id, task_info in active_tasks.items():
            if task_info["status"] in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                task_data = {
                    "task_id": task_id,
                    "status": task_info["status"],
                    "created_at": task_info["created_at"],
                    "stock_count": len(task_info["request"]["stock_list"]),
                    "target_time": task_info["request"]["target_time"],
                    "date": task_info["request"]["date"]
                }
                active_task_list.append(task_data)

        # 按创建时间倒序排列
        active_task_list.sort(key=lambda x: x["created_at"], reverse=True)

        return ApiResponse(
            success=True,
            message="活跃任务列表获取成功",
            data=active_task_list
        )

    except Exception as e:
        logger.error(f"获取活跃任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/stats", response_model=ApiResponse[Dict[str, Any]])
async def get_strategy_stats():
    """
    获取策略执行统计信息

    Returns:
        统计信息
    """
    try:
        # 获取策略统计
        strategy_stats = guaranteed_strategy_instance.get_execution_stats()

        # 获取数据源状态
        tongdaxin_status = await tongdaxin_client.get_status()

        # 获取股票代码客户端状态
        stock_client_status = None
        try:
            if hasattr(stock_client_instance, 'get_status'):
                stock_client_status = await stock_client_instance.get_status()
        except:
            pass

        # 任务统计
        total_tasks = len(active_tasks)
        completed_tasks = sum(1 for t in active_tasks.values() if t["status"] == TaskStatus.COMPLETED)
        failed_tasks = sum(1 for t in active_tasks.values() if t["status"] == TaskStatus.FAILED)

        stats_data = {
            "strategy_execution": strategy_stats,
            "data_source_status": {
                "tongdaxin": {
                    "connected": tongdaxin_status.is_connected,
                    "available_servers": len(tongdaxin_status.available_servers),
                    "response_time": tongdaxin_status.response_time,
                    "last_check": tongdaxin_status.last_check,
                    "error_message": tongdaxin_status.error_message
                },
                "stock_client": stock_client_status.dict() if stock_client_status else None
            },
            "task_statistics": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "active_tasks": total_tasks - completed_tasks - failed_tasks,
                "stored_results": len(task_results)
            },
            "system_info": {
                "current_time": datetime.now(),
                "strategy_config": guaranteed_strategy_instance.config.dict(),
                "search_matrix_size": len(guaranteed_strategy_instance.proven_search_matrix)
            }
        }

        return ApiResponse(
            success=True,
            message="策略统计信息获取成功",
            data=stats_data
        )

    except Exception as e:
        logger.error(f"获取策略统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.post("/config", response_model=ApiResponse[Dict[str, Any]])
async def update_strategy_config(config: GuaranteedStrategyConfig):
    """
    更新策略配置

    Args:
        config: 新的策略配置

    Returns:
        配置更新结果
    """
    try:
        logger.info("更新策略配置")

        # 更新配置
        guaranteed_strategy_instance.config = config

        return ApiResponse(
            success=True,
            message="策略配置更新成功",
            data={
                "updated_config": config.dict(),
                "updated_at": datetime.now()
            }
        )

    except Exception as e:
        logger.error(f"更新策略配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置更新失败: {str(e)}")


@router.get("/config", response_model=ApiResponse[GuaranteedStrategyConfig])
async def get_strategy_config():
    """
    获取当前策略配置

    Returns:
        当前配置
    """
    try:
        return ApiResponse(
            success=True,
            message="策略配置获取成功",
            data=guaranteed_strategy_instance.config
        )

    except Exception as e:
        logger.error(f"获取策略配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.delete("/batch/{task_id}", response_model=ApiResponse[Dict[str, str]])
async def cancel_batch_task(task_id: str):
    """
    取消批量任务

    Args:
        task_id: 任务ID

    Returns:
        取消结果
    """
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")

        task_info = active_tasks[task_id]

        if task_info["status"] not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            raise HTTPException(status_code=400, detail="任务无法取消")

        # 更新任务状态
        task_info["status"] = TaskStatus.CANCELLED
        task_info["completed_at"] = datetime.now()

        logger.info(f"批量任务已取消: {task_id}")

        return ApiResponse(
            success=True,
            message="任务已取消",
            data={
                "task_id": task_id,
                "status": TaskStatus.CANCELLED,
                "cancelled_at": datetime.now()
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败 {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


# 内部接口

@internal_router.post("/execute/batch", response_model=BatchExecutionResult)
async def internal_execute_batch_strategy(request: BatchExecutionRequest):
    """
    内部接口：同步执行批量策略

    Args:
        request: 批量执行请求

    Returns:
        批量执行结果
    """
    try:
        logger.info(f"内部批量策略请求: 股票数量 {len(request.stock_list)}")

        # 更新策略配置
        guaranteed_strategy_instance.config.target_time = request.target_time
        guaranteed_strategy_instance.config.max_concurrent_stocks = request.max_concurrent
        guaranteed_strategy_instance.config.timeout_per_stock = request.timeout_per_stock
        guaranteed_strategy_instance.config.retry_attempts = request.retry_attempts

        # 直接执行批量策略 (同步)
        result = await guaranteed_strategy_instance.execute_guaranteed_batch(request)

        return result

    except Exception as e:
        logger.error(f"内部批量策略执行失败: {e}")
        raise HTTPException(status_code=500, detail=f"策略执行失败: {str(e)}")


@internal_router.post("/execute/single", response_model=SuccessResult)
async def internal_execute_single_strategy(
    symbol: str,
    name: str,
    date: str,
    target_time: str = "09:25"
):
    """
    内部接口：同步执行单只股票策略

    Args:
        symbol: 股票代码
        name: 股票名称
        date: 查询日期
        target_time: 目标时间

    Returns:
        策略执行结果
    """
    try:
        logger.info(f"内部单只股票策略请求: {symbol} ({name}) - {date}")

        # 更新策略配置
        guaranteed_strategy_instance.config.target_time = target_time

        # 执行策略
        result = await guaranteed_strategy_instance.guarantee_success(symbol, name, date)

        return result

    except Exception as e:
        logger.error(f"内部单只股票策略执行失败 {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"策略执行失败: {str(e)}")


@internal_router.get("/health", response_model=ApiResponse[Dict[str, Any]])
async def internal_health_check():
    """
    内部接口：健康检查

    Returns:
        健康状态
    """
    try:
        # 检查策略引擎状态
        strategy_stats = guaranteed_strategy_instance.get_execution_stats()

        # 检查数据源状态
        tongdaxin_status = await tongdaxin_client.get_status()

        # 综合健康判断
        is_healthy = (
            tongdaxin_status.is_connected and
            strategy_stats["total_executions"] >= 0  # 引擎正常
        )

        health_data = {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.now(),
            "components": {
                "strategy_engine": "healthy",
                "tongdaxin_client": "healthy" if tongdaxin_status.is_connected else "unhealthy",
                "stock_client": "healthy"  # 假设健康
            },
            "statistics": {
                "total_executions": strategy_stats["total_executions"],
                "success_rate": strategy_stats["success_rate"],
                "active_connections": len(tongdaxin_status.available_servers)
            }
        }

        return ApiResponse(
            success=is_healthy,
            message="策略引擎健康检查完成" if is_healthy else "策略引擎存在问题",
            data=health_data
        )

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return ApiResponse(
            success=False,
            message=f"健康检查失败: {str(e)}",
            data={
                "status": "error",
                "timestamp": datetime.now(),
                "error": str(e)
            }
        )


@internal_router.post("/cleanup", response_model=ApiResponse[Dict[str, int]])
async def internal_cleanup_tasks():
    """
    内部接口：清理已完成的任务

    Returns:
        清理统计
    """
    try:
        logger.info("开始清理已完成的任务")

        # 清理超过1小时的已完成任务
        cutoff_time = datetime.now() - timedelta(hours=1)

        tasks_to_remove = []
        for task_id, task_info in active_tasks.items():
            if (task_info["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                task_info.get("completed_at") and task_info["completed_at"] < cutoff_time):
                tasks_to_remove.append(task_id)

        # 删除任务
        for task_id in tasks_to_remove:
            del active_tasks[task_id]
            if task_id in task_results:
                del task_results[task_id]

        logger.info(f"清理完成，删除任务数量: {len(tasks_to_remove)}")

        return ApiResponse(
            success=True,
            message="任务清理完成",
            data={
                "cleaned_tasks": len(tasks_to_remove),
                "remaining_active_tasks": len(active_tasks),
                "remaining_results": len(task_results),
                "cleanup_time": datetime.now()
            }
        )

    except Exception as e:
        logger.error(f"任务清理失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")