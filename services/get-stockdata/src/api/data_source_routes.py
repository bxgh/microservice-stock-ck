#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源管理API路由
支持动态配置和管理数据源优先级
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Query, Path, HTTPException
from pydantic import BaseModel

from config.data_source_config import DataSourceConfig, DataCategory, DataSourceStrategy
from services.enhanced_stock_service import EnhancedStockDataService, DataType, MarketType

logger = logging.getLogger(__name__)

# 创建路由器
data_source_router = APIRouter(prefix="/api/v1/datasources", tags=["数据源管理"])

# 初始化服务
config_manager = DataSourceConfig()
stock_service = EnhancedStockDataService()

# 请求模型
class PriorityUpdateRequest(BaseModel):
    """优先级更新请求"""
    category: str
    market: str
    priorities: list[str]

class StrategyUpdateRequest(BaseModel):
    """策略更新请求"""
    category: str
    strategy: str

class SourceConfigRequest(BaseModel):
    """数据源配置请求"""
    source: str
    enabled: bool
    weight: Optional[float] = None
    timeout: Optional[int] = None

@data_source_router.get("/config", summary="获取数据源配置")
async def get_data_source_config():
    """获取完整的数据源配置信息"""
    try:
        config_summary = config_manager.get_config_summary()
        source_status = stock_service.get_source_status()

        return {
            "success": True,
            "message": "获取数据源配置成功",
            "data": {
                "config_summary": config_summary,
                "source_status": source_status,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"获取数据源配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")

@data_source_router.get("/sources", summary="获取数据源列表")
async def get_data_sources():
    """获取所有可用数据源及其元数据"""
    try:
        all_strategies = config_manager.get_all_strategies()
        sources = {}

        for source_name, metadata in config_manager.config["source_metadata"].items():
            sources[source_name] = {
                **metadata,
                "health_status": stock_service.source_health.get(source_name, {})
            }

        return {
            "success": True,
            "message": "获取数据源列表成功",
            "data": {
                "sources": sources,
                "strategies": all_strategies,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"获取数据源列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据源列表失败: {str(e)}")

@data_source_router.get("/priorities/{category}", summary="获取数据源优先级")
async def get_source_priorities(
    category: str = Path(..., description="数据分类"),
    market: str = Query("A股", description="市场类型"),
    strategy: Optional[str] = Query(None, description="指定策略")
):
    """获取指定分类的数据源优先级"""
    try:
        # 验证分类是否存在
        if category not in [c.value for c in DataCategory]:
            available_categories = [c.value for c in DataCategory]
            raise HTTPException(
                status_code=400,
                detail=f"无效的数据分类 '{category}'。可用分类: {available_categories}"
            )

        data_category = DataCategory(category)
        priorities = config_manager.get_priority_sources(data_category, market, strategy)
        settings = config_manager.get_source_settings(data_category)

        return {
            "success": True,
            "message": f"获取 {category} 数据源优先级成功",
            "data": {
                "category": category,
                "market": market,
                "strategy": strategy or config_manager.config["strategies"][category].get("default_strategy"),
                "priorities": priorities,
                "settings": settings,
                "timestamp": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据源优先级失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取优先级失败: {str(e)}")

@data_source_router.put("/priorities", summary="更新数据源优先级")
async def update_source_priorities(request: PriorityUpdateRequest):
    """更新数据源优先级配置"""
    try:
        # 验证分类
        if request.category not in [c.value for c in DataCategory]:
            available_categories = [c.value for c in DataCategory]
            raise HTTPException(
                status_code=400,
                detail=f"无效的数据分类 '{request.category}'。可用分类: {available_categories}"
            )

        # 验证数据源
        available_sources = list(config_manager.config["source_metadata"].keys())
        invalid_sources = [s for s in request.priorities if s not in available_sources]
        if invalid_sources:
            raise HTTPException(
                status_code=400,
                detail=f"无效的数据源: {invalid_sources}。可用数据源: {available_sources}"
            )

        data_category = DataCategory(request.category)
        config_manager.update_source_priority(data_category, request.market, request.priorities)

        return {
            "success": True,
            "message": f"更新 {request.category} - {request.market} 数据源优先级成功",
            "data": {
                "category": request.category,
                "market": request.market,
                "new_priorities": request.priorities,
                "timestamp": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新数据源优先级失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新优先级失败: {str(e)}")

@data_source_router.put("/strategy", summary="更新数据分类策略")
async def update_category_strategy(request: StrategyUpdateRequest):
    """更新数据分类的默认策略"""
    try:
        # 验证分类
        if request.category not in [c.value for c in DataCategory]:
            available_categories = [c.value for c in DataCategory]
            raise HTTPException(
                status_code=400,
                detail=f"无效的数据分类 '{request.category}'。可用分类: {available_categories}"
            )

        # 验证策略
        available_strategies = list(config_manager.config["strategy_profiles"].keys())
        if request.strategy not in available_strategies:
            raise HTTPException(
                status_code=400,
                detail=f"无效的策略 '{request.strategy}'。可用策略: {available_strategies}"
            )

        data_category = DataCategory(request.category)
        config_manager.update_category_strategy(data_category, request.strategy)

        return {
            "success": True,
            "message": f"更新 {request.category} 数据分类策略成功",
            "data": {
                "category": request.category,
                "new_strategy": request.strategy,
                "timestamp": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新数据分类策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新策略失败: {str(e)}")

@data_source_router.get("/health/{source}", summary="获取数据源健康状态")
async def get_source_health(source: str = Path(..., description="数据源名称")):
    """获取指定数据源的健康状态"""
    try:
        if source not in stock_service.source_health:
            raise HTTPException(status_code=404, detail=f"数据源 '{source}' 不存在")

        health_info = stock_service.source_health[source]
        metadata = config_manager.get_source_metadata(source)

        return {
            "success": True,
            "message": f"获取数据源 {source} 健康状态成功",
            "data": {
                "source": source,
                "health": health_info,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据源健康状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取健康状态失败: {str(e)}")

@data_source_router.get("/test/{symbol}", summary="测试数据源获取")
async def test_data_sources(
    symbol: str = Path(..., description="股票代码"),
    data_type: str = Query("realtime", description="数据类型: realtime, historical, tick, financial"),
    strategy: Optional[str] = Query(None, description="测试策略")
):
    """测试不同数据源获取指定股票数据"""
    try:
        # 验证数据类型
        available_types = [dt.value for dt in DataType]
        if data_type not in available_types:
            raise HTTPException(
                status_code=400,
                detail=f"无效的数据类型 '{data_type}'。可用类型: {available_types}"
            )

        data_type_enum = DataType(data_type)
        market_type = stock_service.detect_market_type(symbol)

        # 根据数据类型确定数据分类
        category_mapping = {
            DataType.REALTIME: DataCategory.PRICE_DATA,
            DataType.HISTORICAL: DataCategory.PRICE_DATA,
            DataType.TICK: DataCategory.VOLUME_DATA,
            DataType.FINANCIAL: DataCategory.FINANCIAL_DATA
        }
        category = category_mapping.get(data_type_enum, DataCategory.MARKET_DATA)

        # 获取优先级数据源
        priorities = config_manager.get_priority_sources(category, market_type.value, strategy)

        test_results = []
        for source in priorities:
            try:
                start_time = datetime.now()

                if data_type == "realtime":
                    data = await stock_service.get_realtime_data(symbol)
                elif data_type == "historical":
                    data = await stock_service.get_historical_data(symbol)
                elif data_type == "tick":
                    data = await stock_service.get_tick_data(symbol)
                elif data_type == "financial":
                    data = await stock_service.get_financial_data(symbol)
                else:
                    data = None

                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()

                if data:
                    test_results.append({
                        "source": source,
                        "status": "success",
                        "response_time": response_time,
                        "data_source": data.get("data_source", "unknown"),
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    test_results.append({
                        "source": source,
                        "status": "failed",
                        "response_time": response_time,
                        "error": "无数据返回",
                        "timestamp": datetime.now().isoformat()
                    })

            except Exception as e:
                test_results.append({
                    "source": source,
                    "status": "error",
                    "response_time": 0,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

        return {
            "success": True,
            "message": f"测试股票 {symbol} 数据源完成",
            "data": {
                "symbol": symbol,
                "data_type": data_type,
                "market_type": market_type.value,
                "category": category.value,
                "strategy": strategy or "default",
                "test_results": test_results,
                "summary": {
                    "total_sources": len(test_results),
                    "successful_sources": len([r for r in test_results if r["status"] == "success"]),
                    "failed_sources": len([r for r in test_results if r["status"] in ["failed", "error"]]),
                    "average_response_time": sum(r["response_time"] for r in test_results) / len(test_results)
                },
                "timestamp": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试数据源失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")

@data_source_router.get("/categories", summary="获取数据分类列表")
async def get_data_categories():
    """获取所有可用的数据分类"""
    try:
        categories = []
        for category in DataCategory:
            category_config = config_manager.config["strategies"].get(category.value, {})
            categories.append({
                "name": category.value,
                "description": category_config.get("description", ""),
                "default_strategy": category_config.get("default_strategy"),
                "supported_markets": list(category_config.get("priorities", {}).keys())
            })

        return {
            "success": True,
            "message": "获取数据分类列表成功",
            "data": {
                "categories": categories,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"获取数据分类失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取分类失败: {str(e)}")

@data_source_router.get("/strategies", summary="获取策略列表")
async def get_strategies():
    """获取所有可用的数据源策略"""
    try:
        strategies = config_manager.get_all_strategies()

        return {
            "success": True,
            "message": "获取策略列表成功",
            "data": {
                "strategies": strategies,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略失败: {str(e)}")