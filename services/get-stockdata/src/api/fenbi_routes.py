#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fenbi API路由
基于FenbiEngine的REST API接口，提供股票分笔数据服务
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from typing import List, Optional
import logging
from datetime import datetime

try:
    from ..services.fenbi_engine import FenbiEngine
    from ..models.tick_models import (
        TickDataRequest, TickDataResponse, TickDataBatchRequest,
        TickDataBatchResponse, TickDataSummary, DataSourceStatus,
        TickDataFilter, TickDataStatistics
    )
    from ..models.stock_models import StockInfo
except ImportError:
    from services.fenbi_engine import FenbiEngine
    from models.tick_models import (
        TickDataRequest, TickDataResponse, TickDataBatchRequest,
        TickDataBatchResponse, TickDataSummary, DataSourceStatus,
        TickDataFilter, TickDataStatistics
    )
    from models.stock_models import StockInfo

logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter(prefix="/api/v1/fenbi", tags=["分笔数据"])  # 统一的分笔数据接口
internal_router = APIRouter(prefix="/internal/fenbi", tags=["分笔数据内部接口"])

# 全局FenbiEngine实例
fenbi_engine = None


async def get_fenbi_engine():
    """获取Fenbi引擎实例依赖"""
    global fenbi_engine
    if fenbi_engine is None:
        try:
            # 使用默认数据源 (工厂会返回mootdx)
            fenbi_engine = FenbiEngine()
            logger.info(f"创建Fenbi引擎，数据源: {fenbi_engine.data_source.source_name}")
        except Exception as e:
            logger.error(f"创建FenbiEngine失败: {e}")
            raise HTTPException(status_code=500, detail="服务初始化失败")

    # 每次都确保连接正常
    try:
        if not fenbi_engine.data_source.is_connected:
            await fenbi_engine.data_source.connect()
            logger.info(f"数据源连接成功: {fenbi_engine.data_source.source_name}")
    except Exception as e:
        logger.error(f"数据源连接失败: {e}")
        # 尝试重新创建引擎
        try:
            fenbi_engine = FenbiEngine()
            await fenbi_engine.data_source.connect()
            logger.info(f"重新创建并连接Fenbi引擎成功")
        except Exception as e2:
            logger.error(f"重新创建FenbiEngine失败: {e2}")
            raise HTTPException(status_code=500, detail="数据源连接失败")

    return fenbi_engine


def convert_to_response(data_list):
    """将引擎返回的数据转换为API响应格式"""
    if not data_list:
        return []

    response_data = []
    for item in data_list:
        response_item = {
            "time": getattr(item, 'time', ''),
            "price": float(getattr(item, 'price', 0)),
            "volume": int(getattr(item, 'volume', 0)),
            "amount": float(getattr(item, 'amount', 0)),
            "direction": getattr(item, 'direction', 'N'),
            "code": getattr(item, 'code', ''),
            "date": getattr(item, 'date', '')
        }
        response_data.append(response_item)

    return response_data


@router.get("/{symbol}/date/{date}")
async def get_fenbi_tick_data(
    symbol: str = Path(..., description="股票代码"),
    date: str = Path(..., description="交易日期 (YYYYMMDD)"),
    market: Optional[str] = Query(None, description="市场代码 (SH/SZ)"),
    enable_time_sort: bool = Query(True, description="是否启用时间排序"),
    enable_deduplication: bool = Query(True, description="是否启用数据去重"),
    engine=Depends(get_fenbi_engine)
):
    """
    获取Fenbi分笔数据

    使用重构后的FenbiEngine获取股票分笔数据，支持时间排序和去重
    """
    try:
        # 获取数据
        data = await engine.get_tick_data(
            symbol=symbol,
            date=date,
            market=market,
            enable_time_sort=enable_time_sort,
            enable_deduplication=enable_deduplication
        )

        # 获取统计信息
        stats = engine.get_stats()

        # 生成增强报告
        enhanced_report = engine.generate_enhanced_report(data)

        # 构建响应
        return {
            "success": True,
            "message": f"获取股票 {symbol} 分笔数据成功",
            "data": {
                "symbol": symbol,
                "date": date,
                "market": market,
                "records": convert_to_response(data),
                "total_count": len(data),
                "unique_count": stats.get('unique_records', len(data)),
                "duplicates_removed": stats.get('duplicates_removed', 0),
                "processing_stats": stats,
                "quality_report": enhanced_report
            }
        }

    except Exception as e:
        logger.error(f"获取股票 {symbol} Fenbi分笔数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取分笔数据失败: {str(e)}")


@router.get("/{symbol}/date/{date}/summary")
async def get_fenbi_tick_summary(
    symbol: str = Path(..., description="股票代码"),
    date: str = Path(..., description="交易日期 (YYYYMMDD)"),
    market: Optional[str] = Query(None, description="市场代码 (SH/SZ)"),
    engine=Depends(get_fenbi_engine)
):
    """
    获取Fenbi分笔数据摘要

    返回数据的统计摘要信息，不包含详细记录
    """
    try:
        # 获取数据
        data = await engine.get_tick_data(
            symbol=symbol,
            date=date,
            market=market,
            enable_time_sort=True,
            enable_deduplication=True
        )

        # 获取统计信息
        stats = engine.get_stats()

        # 生成增强报告
        enhanced_report = engine.generate_enhanced_report(data)

        # 构建摘要响应
        return {
            "success": True,
            "message": f"获取股票 {symbol} 分笔数据摘要成功",
            "data": {
                "symbol": symbol,
                "date": date,
                "market": market,
                "record_count": len(data),
                "unique_count": stats.get('unique_records', len(data)),
                "duplicates_removed": stats.get('duplicates_removed', 0),
                "processing_time": stats.get('duration', 0),
                "quality_score": enhanced_report['basic_quality']['completeness_score'],
                "quality_grade": enhanced_report['basic_quality']['quality_grade'],
                "time_coverage": enhanced_report['basic_quality']['time_coverage']
            }
        }

    except Exception as e:
        logger.error(f"获取股票 {symbol} Fenbi分笔数据摘要失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据摘要失败: {str(e)}")


@router.get("/engine/stats")
async def get_engine_stats(engine=Depends(get_fenbi_engine)):
    """
    获取Fenbi引擎统计信息

    返回引擎的性能和状态信息
    """
    try:
        stats = engine.get_stats()
        data_source_info = {
            "name": engine.data_source.source_name,
            "connected": engine.data_source.is_connected,
            "type": type(engine.data_source).__name__
        }

        return {
            "success": True,
            "data": {
                "engine_stats": stats,
                "data_source": data_source_info
            }
        }

    except Exception as e:
        logger.error(f"获取引擎统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取引擎统计失败: {str(e)}")


@router.post("/batch")
async def get_batch_fenbi_data(
    requests: List[dict],
    engine=Depends(get_fenbi_engine)
):
    """
    批量获取Fenbi分笔数据

    支持一次性处理多个股票代码的请求
    """
    try:
        results = []

        for request_item in requests:
            symbol = request_item.get('symbol')
            date = request_item.get('date')
            market = request_item.get('market')

            if not symbol or not date:
                results.append({
                    "symbol": symbol,
                    "success": False,
                    "error": "缺少必要参数 symbol 或 date"
                })
                continue

            try:
                # 获取数据
                data = await engine.get_tick_data(
                    symbol=symbol,
                    date=date,
                    market=market,
                    enable_time_sort=True,
                    enable_deduplication=True
                )

                stats = engine.get_stats()

                results.append({
                    "symbol": symbol,
                    "success": True,
                    "record_count": len(data),
                    "unique_count": stats.get('unique_records', len(data)),
                    "processing_time": stats.get('duration', 0)
                })

            except Exception as e:
                logger.error(f"批量处理股票 {symbol} 失败: {e}")
                results.append({
                    "symbol": symbol,
                    "success": False,
                    "error": str(e)
                })

        return {
            "success": True,
            "message": "批量获取Fenbi分笔数据完成",
            "results": results
        }

    except Exception as e:
        logger.error(f"批量获取Fenbi分笔数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量处理失败: {str(e)}")


# 内部接口
@internal_router.post("/test")
async def test_fenbi_engine(engine=Depends(get_fenbi_engine)):
    """
    测试Fenbi引擎连接和功能
    """
    try:
        # 使用测试数据
        test_symbol = "000001"
        test_date = "20251120"

        data = await engine.get_tick_data(
            symbol=test_symbol,
            date=test_date,
            enable_time_sort=True,
            enable_deduplication=True
        )

        stats = engine.get_stats()

        return {
            "success": True,
            "message": "Fenbi引擎测试成功",
            "test_data": {
                "symbol": test_symbol,
                "date": test_date,
                "records_count": len(data),
                "engine_stats": stats
            }
        }

    except Exception as e:
        logger.error(f"Fenbi引擎测试失败: {e}")
        return {
            "success": False,
            "message": f"Fenbi引擎测试失败: {str(e)}"
        }


@internal_router.post("/reset")
async def reset_fenbi_engine():
    """
    重置Fenbi引擎
    """
    global fenbi_engine
    try:
        if fenbi_engine:
            await fenbi_engine.close()

        fenbi_engine = None
        return {
            "success": True,
            "message": "Fenbi引擎重置成功"
        }

    except Exception as e:
        logger.error(f"重置Fenbi引擎失败: {e}")
        return {
            "success": False,
            "message": f"重置失败: {str(e)}"
        }