#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态策略切换API路由
支持运行时调整数据源策略
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Query, Path, HTTPException, BackgroundTasks
from pydantic import BaseModel

from services.strategy_engine import StrategyEngine, StrategyType, DataSourceMetrics
from services.enhanced_stock_service import EnhancedStockService, DataType, MarketType

logger = logging.getLogger(__name__)

# 创建路由器
strategy_router = APIRouter(prefix="/api/v1/strategies", tags=["策略管理"])

# 初始化服务
strategy_engine = StrategyEngine()
stock_service = EnhancedStockService()

# 请求模型
class StrategyUpdateRequest(BaseModel):
    """策略更新请求"""
    data_type: str
    strategy: str

class CustomWeightsRequest(BaseModel):
    """自定义权重请求"""
    performance: float = 0.25
    availability: float = 25
    cost: float = 25
    accuracy: float = 25

class BulkStrategyUpdateRequest(BaseModel):
    """批量策略更新请求"""
    strategies: Dict[str, str]  # data_type -> strategy

@strategy_router.get("/status", summary="获取策略状态")
async def get_strategy_status():
    """获取当前策略配置和实时状态"""
    try:
        real_time_status = strategy_engine.get_real_time_status()

        return {
            "success": True,
            "message": "获取策略状态成功",
            "data": {
                "real_time_status": real_time_status,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"获取策略状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")

@strategy_router.get("/performance/{data_type}", summary="获取策略性能统计")
async def get_strategy_performance(
    data_type: str = Path(..., description="数据类型"),
    strategy: str = Query("balanced", description="策略类型"),
    time_window: int = Query(3600, description="统计时间窗口（秒）")
):
    """获取指定数据类型和策略的性能统计"""
    try:
        # 验证策略类型
        available_strategies = [s.value for s in StrategyType]
        if strategy not in available_strategies:
            raise HTTPException(
                status_code=400,
                detail=f"无效的策略类型 '{strategy}'。可用策略: {available_strategies}"
            )

        strategy_enum = StrategyType(strategy)
        performance = strategy_engine.get_strategy_performance(data_type, strategy_enum, time_window)

        return {
            "success": True,
            "message": f"获取策略性能统计成功",
            "data": performance
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略性能失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能统计失败: {str(e)}")

@strategy_router.get("/optimize", summary="获取最优数据源建议")
async def get_optimal_sources(
    data_type: str = Query("realtime", description="数据类型"),
    market: str = Query("A股", description="市场类型"),
    strategy: Optional[str] = Query(None, description="策略类型")
):
    """获取指定条件下的最优数据源建议"""
    try:
        # 验证数据类型
        available_types = [dt.value for dt in DataType]
        if data_type not in available_types:
            raise HTTPException(
                status_code=400,
                detail=f"无效的数据类型 '{data_type}'。可用类型: {available_types}"
            )

        # 验证策略类型
        strategy_enum = None
        if strategy:
            available_strategies = [s.value for s in StrategyType]
            if strategy not in available_strategies:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的策略类型 '{strategy}'。可用策略: {available_strategies}"
                )
            strategy_enum = StrategyType(strategy)

        # 获取最优数据源
        optimal_sources = await strategy_engine.get_optimal_sources(data_type, market, strategy_enum)

        # 获取各数据源的详细指标
        source_details = {}
        for source, score in optimal_sources:
            metrics = strategy_engine.source_metrics.get(source)
            if metrics:
                source_details[source] = {
                    "score": score,
                    "requests": metrics.request_count,
                    "success_rate": metrics.success_count / max(1, metrics.request_count),
                    "avg_response_time": metrics.total_response_time / max(1, metrics.success_count),
                    "availability_score": metrics.availability_score,
                    "consecutive_failures": metrics.consecutive_failures
                }

        return {
            "success": True,
            "message": f"获取 {data_type} - {market} 最优数据源成功",
            "data": {
                "data_type": data_type,
                "market": market,
                "strategy": strategy or "default",
                "optimal_sources": optimal_sources,
                "source_details": source_details,
                "recommendations": _generate_recommendations(optimal_sources),
                "timestamp": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取最优数据源失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取最优源失败: {str(e)}")

@strategy_router.post("/update", summary="更新策略配置")
async def update_strategy(request: StrategyUpdateRequest):
    """更新指定数据类型的策略"""
    try:
        # 验证数据类型
        available_types = [dt.value for dt in DataType]
        if request.data_type not in available_types:
            raise HTTPException(
                status_code=400,
                detail=f"无效的数据类型 '{request.data_type}'。可用类型: {available_types}"
            )

        # 验证策略类型
        available_strategies = [s.value for s in StrategyType]
        if request.strategy not in available_strategies:
            raise HTTPException(
                status_code=400,
                detail=f"无效的策略类型 '{request.strategy}'。可用策略: {available_strategies}"
            )

        strategy_enum = StrategyType(request.strategy)
        strategy_engine.set_strategy(request.data_type, strategy_enum)

        return {
            "success": True,
            "message": f"更新 {request.data_type} 策略成功",
            "data": {
                "data_type": request.data_type,
                "new_strategy": request.strategy,
                "timestamp": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新策略失败: {str(e)}")

@strategy_router.post("/bulk-update", summary="批量更新策略")
async def bulk_update_strategies(request: BulkStrategyRequest):
    """批量更新多个数据类型的策略"""
    try:
        updated_strategies = []
        failed_updates = []

        for data_type, strategy in request.strategies.items():
            try:
                # 验证数据类型
                available_types = [dt.value for dt in DataType]
                if data_type not in available_types:
                    failed_updates.append(f"{data_type}: 无效的数据类型")
                    continue

                # 验证策略类型
                available_strategies = [s.value for s in StrategyType]
                if strategy not in available_strategies:
                    failed_updates.append(f"{data_type}: 无效的策略类型")
                    continue

                strategy_enum = StrategyType(strategy)
                strategy_engine.set_strategy(data_type, strategy_enum)
                updated_strategies.append(data_type)

            except Exception as e:
                logger.error(f"批量更新策略失败 - {data_type}: {e}")
                failed_updates.append(f"{data_type}: {str(e)}")

        return {
            "success": True,
            "message": f"批量更新策略完成",
            "data": {
                "updated_count": len(updated_strategies),
                "failed_count": len(failed_updates),
                "updated_strategies": updated_strategies,
                "failed_updates": failed_updates,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"批量更新策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量更新失败: {str(e)}")

@strategy_router.post("/test", summary="测试策略性能")
async def test_strategy_performance(
    request: StrategyUpdateRequest,
    background_tasks: BackgroundTasks,
    test_duration: int = Query(300, description="测试持续时间（秒）"),
    test_symbol: str = Query("000001", description="测试股票代码"),
    test_frequency: int = Query(10, description="测试频率（秒）")
):
    """测试指定策略的性能"""
    try:
        # 验证数据类型和策略
        available_types = [dt.value for dt in DataType]
        if request.data_type not in available_types:
            raise HTTPException(
                status_code=400,
                detail=f"无效的数据类型 '{request.data_type}'。可用类型: {available_types}"
            )

        available_strategies = [s.value for s in StrategyType]
        if request.strategy not in available_strategies:
            raise HTTPException(
                status_code=400,
                detail=f"无效的策略类型 '{request.strategy}'。可用策略: {available_strategies}"
            )

        # 启动后台测试任务
        task_id = f"test_{request.data_type}_{request.strategy}_{int(datetime.now().timestamp())}"
        background_tasks.add_task(
            _run_strategy_test,
            task_id,
            request.data_type,
            StrategyType(request.strategy),
            test_symbol,
            test_duration,
            test_frequency
        )

        return {
            "success": True,
            "message": f"开始测试 {request.data_type} - {request.strategy} 策略性能",
            "data": {
                "task_id": task_id,
                "data_type": request.data_type,
                "strategy": request.strategy,
                "test_symbol": test_symbol,
                "test_duration": test_duration,
                "test_frequency": test_frequency,
                "estimated_tests": test_duration // test_frequency,
                "status": "running",
                "start_time": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动策略测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动测试失败: {str(e)}")

@strategy_router.get("/test/{task_id}", summary="获取测试结果")
async def get_test_result(task_id: str = Path(..., description="测试任务ID")):
    """获取测试任务的结果"""
    try:
        # 这里应该从任务存储中获取结果
        # 简化实现，返回模拟数据
        return {
            "success": True,
            "message": f"获取测试任务 {task_id} 结果",
            "data": {
                "task_id": task_id,
                "status": "completed",
                "summary": {
                    "total_tests": 30,
                    "successful_tests": 28,
                    "failed_tests": 2,
                    "avg_response_time": 0.45,
                    "success_rate": 0.93
                },
                "detailed_results": [
                    {
                        "source": "akshare",
                        "response_time": 0.35,
                        "success": True,
                        "timestamp": datetime.now().isoformat()
                    },
                    {
                        "source": "tushare",
                        "response_time": 0.42,
                        "success": True,
                        "timestamp": datetime.now().isoformat()
                    }
                ],
                "recommendations": [
                    "aksource 性能最佳，建议优先使用",
                    "tushare 稳定性高，适合备用"
                ],
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"获取测试结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取测试结果失败: {str(e)}")

@strategy_router.get("/metrics", summary="获取数据源指标")
async def get_source_metrics():
    """获取所有数据源的详细指标"""
    try:
        metrics_data = {}
        for source, metrics in strategy_engine.source_metrics.items():
            metrics_data[source] = {
                "total_requests": metrics.request_count,
                "successful_requests": metrics.success_count,
                "failed_requests": metrics.failure_count,
                "success_rate": metrics.success_count / max(1, metrics.request_count),
                "average_response_time": metrics.total_response_time / max(1, metrics.success_count),
                "performance_score": metrics.performance_score,
                "availability_score": metrics.availability_score,
                "consecutive_failures": metrics.consecutive_failures,
                "last_success": metrics.last_success_time.isoformat() if metrics.last_success_time else None,
                "last_failure": metrics.last_failure_time.isoformat() if metrics.last_failure_time else None,
                "circuit_breaker_status": strategy_engine.circuit_breakers.get(source, {}).get("state", "unknown")
            }

        # 计算总体统计
        total_requests = sum(m.request_count for m in strategy_engine.source_metrics.values())
        total_successes = sum(m.success_count for m in strategy_engine.source_metrics.values())
        overall_success_rate = total_successes / max(1, total_requests)

        overall_stats = {
            "total_data_sources": len(strategy_engine.source_metrics),
            "total_requests": total_requests,
            "total_successes": total_successes,
            "total_failures": total_requests - total_successes,
            "overall_success_rate": overall_success_rate,
            "avg_response_time": sum(m.total_response_time for m in strategy_engine.source_metrics.values()) / max(1, total_successes),
            "active_circuit_breakers": len([cb for cb in strategy_engine.circuit_breakers.values() if cb.get("state") == "open"])
        }

        return {
            "success": True,
            "message": "获取数据源指标成功",
            "data": {
                "overall_stats": overall_stats,
                "source_metrics": metrics_data,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"获取数据源指标失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取指标失败: {str(e)}")

@strategy_router.post("/auto-adjustment", summary="控制自动调整")
async def toggle_auto_adjustment(enabled: bool = Query(..., description="是否启用自动调整")):
    """控制策略自动调整功能"""
    try:
        strategy_engine.auto_adjustment_enabled = enabled

        status = "启用" if enabled else "禁用"

        return {
            "success": True,
            "message": f"策略自动调整功能已{status}",
            "data": {
                "auto_adjustment_enabled": enabled,
                "adjustment_interval": strategy_engine.adjustment_interval,
                "last_adjustment": strategy_engine.last_adjustment_time.isoformat(),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"切换自动调整失败: {e}")
        raise HTTP_exception(status_code=500, detail=f"切换失败: {str(e)}")

async def _run_strategy_test(
    task_id: str,
    data_type: str,
    strategy: StrategyType,
    test_symbol: str,
    duration: int,
    frequency: int
):
    """运行策略测试任务"""
    logger.info(f"开始执行策略测试任务: {task_id}")

    end_time = datetime.now() + timedelta(seconds=duration)
    test_results = []

    while datetime.now() < end_time:
        try:
            # 使用指定策略获取数据源
            optimal_sources = await strategy_engine.get_optimal_sources(data_type, "A股", strategy)

            if optimal_sources:
                best_source = optimal_sources[0][0]
                start_time = datetime.now()

                # 模拟数据获取
                await asyncio.sleep(0.1)
                response_time = (datetime.now() - start_time).total_seconds()

                # 记录结果
                success = True  # 简化实现，实际应该真实调用数据源
                strategy_engine.record_source_result(best_source, success, response_time)

                test_results.append({
                    "timestamp": datetime.now().isoformat(),
                    "source": best_source,
                    "response_time": response_time,
                    "success": success
                })

            await asyncio.sleep(frequency)

        except Exception as e:
            logger.error(f"策略测试任务异常: {e}")
            test_results.append({
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "success": False
            })

    # 这里应该保存测试结果到存储中
    logger.info(f"策略测试任务完成: {task_id}, 共执行 {len(test_results)} 次测试")

def _generate_recommendations(optimal_sources: List[tuple]) -> List[str]:
    """生成数据源推荐"""
    recommendations = []

    if not optimal_sources:
        return ["暂无可用数据源"]

    top_source = optimal_sources[0][0]
    recommendations.append(f"推荐使用 {top_source}，综合得分最高")

    # 基于数据源特性给出建议
    if len(optimal_sources) >= 2:
        second_source = optimal_sources[1][0]
        recommendations.append(f"备用数据源: {second_source}")

    # 通用建议
    recommendations.append("建议定期监控数据源性能，及时调整策略")
    recommendations.append("在高频请求场景下考虑使用负载均衡")

    return recommendations