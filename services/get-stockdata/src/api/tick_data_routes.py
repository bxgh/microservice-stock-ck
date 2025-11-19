#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
分笔数据API路由
提供股票分笔交易数据相关的REST API接口
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends, BackgroundTasks
from typing import List, Optional
import logging
from datetime import datetime, date

try:
    from ..services.tongdaxin_client import tongdaxin_client
    from ..services.stock_code_client import stock_client_instance
    from ..models.tick_models import (
        TickDataRequest, TickDataResponse, TickDataBatchRequest,
        TickDataBatchResponse, TickDataSummary, DataSourceStatus,
        TickDataFilter, TickDataStatistics
    )
    from ..models.stock_models import StockInfo
except ImportError:
    # 测试时使用绝对导入
    from services.tongdaxin_client import tongdaxin_client
    from services.stock_code_client import stock_client_instance
    from models.tick_models import (
        TickDataRequest, TickDataResponse, TickDataBatchRequest,
        TickDataBatchResponse, TickDataSummary, DataSourceStatus,
        TickDataFilter, TickDataStatistics
    )
    from models.stock_models import StockInfo

logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter(prefix="/api/v1/ticks", tags=["分笔数据"])
internal_router = APIRouter(prefix="/internal/ticks", tags=["内部接口"])


async def get_tongdaxin_client():
    """获取通达信客户端实例依赖"""
    return tongdaxin_client


async def get_stock_client():
    """获取股票客户端实例依赖"""
    return stock_client_instance


@router.post("/{stock_code}", response_model=TickDataResponse)
async def get_stock_tick_data(
    stock_code: str = Path(..., description="股票代码"),
    trade_date: date = Query(..., description="交易日期"),
    market: str = Query(None, description="市场代码 (SH/SZ/BJ)"),
    include_auction: bool = Query(True, description="是否包含集合竞价"),
    tongdaxin_client=Depends(get_tongdaxin_client)
):
    """
    获取单只股票分笔数据

    根据股票代码和日期获取详细的分笔交易数据
    """
    try:
        # 确定市场代码
        if not market:
            if stock_code.startswith(('60', '68', '90')):
                market = "SH"
            elif stock_code.startswith(('00', '30')):
                market = "SZ"
            else:
                market = "BJ"  # 默认为北交所

        # 构建请求
        request = TickDataRequest(
            stock_code=stock_code,
            date=datetime.combine(trade_date, datetime.min.time()),
            market=market,
            include_auction=include_auction
        )

        # 获取分笔数据
        response = await tongdaxin_client.get_tick_data(request)

        return response

    except Exception as e:
        logger.error(f"获取股票 {stock_code} 分笔数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取分笔数据失败: {str(e)}")


@router.post("/batch", response_model=TickDataBatchResponse)
async def get_batch_tick_data(
    request: TickDataBatchRequest,
    tongdaxin_client=Depends(get_tongdaxin_client)
):
    """
    批量获取多只股票分笔数据

    支持一次性获取多只股票的分笔数据，提高查询效率
    """
    try:
        response = await tongdaxin_client.get_batch_tick_data(request)
        return response

    except Exception as e:
        logger.error(f"批量获取分笔数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量获取失败: {str(e)}")


@router.post("/exchange/{exchange}", response_model=TickDataBatchResponse)
async def get_exchange_tick_data(
    exchange: str = Path(..., description="交易所代码 (SH/SZ/BJ)"),
    trade_date: date = Query(..., description="交易日期"),
    limit: int = Query(50, ge=1, le=200, description="获取股票数量限制"),
    include_auction: bool = Query(True, description="是否包含集合竞价"),
    stock_client=Depends(get_stock_client),
    tongdaxin_client=Depends(get_tongdaxin_client)
):
    """
    按交易所获取分笔数据

    获取指定交易所的所有股票分笔数据
    """
    try:
        # 初始化股票客户端
        await stock_client.initialize()

        # 获取指定交易所的股票列表
        stocks = await stock_client.get_stocks_by_exchange(exchange)
        limited_stocks = stocks[:limit]

        if not limited_stocks:
            raise HTTPException(status_code=404, detail=f"未找到交易所 {exchange} 的股票数据")

        # 构建批量请求
        stock_codes = [stock.stock_code for stock in limited_stocks]
        batch_request = TickDataBatchRequest(
            stock_codes=stock_codes,
            date=datetime.combine(trade_date, datetime.min.time()),
            include_auction=include_auction
        )

        # 批量获取分笔数据
        response = await tongdaxin_client.get_batch_tick_data(batch_request)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取交易所 {exchange} 分笔数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取交易所数据失败: {str(e)}")


@router.get("/status", response_model=DataSourceStatus)
async def get_tick_data_status(tongdaxin_client=Depends(get_tongdaxin_client)):
    """
    获取分笔数据源状态

    检查通达信数据源的连接状态和可用性
    """
    try:
        status = await tongdaxin_client.get_status()
        return status

    except Exception as e:
        logger.error(f"获取数据源状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/status/refresh")
async def refresh_tick_data_connection(tongdaxin_client=Depends(get_tongdaxin_client)):
    """
    刷新分笔数据源连接

    重新初始化通达信客户端连接
    """
    try:
        # 关闭现有连接
        await tongdaxin_client.close()

        # 重新初始化
        success = await tongdaxin_client.initialize()

        if success:
            return {
                "success": True,
                "message": "通达信连接刷新成功",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "通达信连接刷新失败",
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"刷新连接失败: {e}")
        raise HTTPException(status_code=500, detail=f"刷新连接失败: {str(e)}")


@router.get("/{stock_code}/summary")
async def get_tick_data_summary(
    stock_code: str = Path(..., description="股票代码"),
    trade_date: date = Query(..., description="交易日期"),
    market: str = Query(None, description="市场代码 (SH/SZ/BJ)"),
    include_auction: bool = Query(True, description="是否包含集合竞价"),
    tongdaxin_client=Depends(get_tongdaxin_client)
):
    """
    获取股票分笔数据摘要

    计算并返回分笔数据的统计摘要信息
    """
    try:
        # 确定市场代码
        if not market:
            if stock_code.startswith(('60', '68', '90')):
                market = "SH"
            elif stock_code.startswith(('00', '30')):
                market = "SZ"
            else:
                market = "BJ"

        # 获取分笔数据
        request = TickDataRequest(
            stock_code=stock_code,
            date=datetime.combine(trade_date, datetime.min.time()),
            market=market,
            include_auction=include_auction
        )

        response = await tongdaxin_client.get_tick_data(request)

        if not response.success or not response.data:
            raise HTTPException(status_code=404, detail=f"未找到 {stock_code} 的分笔数据")

        # 计算摘要
        from ..models.tick_models import TickDataAdapter
        summary = TickDataAdapter.calculate_summary(
            response.data, stock_code, request.date
        )

        return {
            "success": True,
            "message": f"成功获取 {stock_code} 分笔数据摘要",
            "data": summary.dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分笔数据摘要失败 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=f"获取摘要失败: {str(e)}")


# 内部接口 - 供微服务内部使用

@internal_router.post("/fetch-and-store")
async def fetch_and_store_tick_data(
    stock_code: str,
    trade_date: date,
    market: str = None,
    include_auction: bool = True,
    tongdaxin_client=Depends(get_tongdaxin_client)
):
    """
    内部接口：获取并存储分笔数据

    供其他微服务调用的内部接口，获取分笔数据并存储到数据库
    """
    try:
        # 确定市场代码
        if not market:
            if stock_code.startswith(('60', '68', '90')):
                market = "SH"
            elif stock_code.startswith(('00', '30')):
                market = "SZ"
            else:
                market = "BJ"

        request = TickDataRequest(
            stock_code=stock_code,
            date=datetime.combine(trade_date, datetime.min.time()),
            market=market,
            include_auction=include_auction
        )

        response = await tongdaxin_client.get_tick_data(request)

        # TODO: 这里可以添加数据存储逻辑
        # await store_tick_data_to_db(response.data)

        return {
            "success": response.success,
            "stock_code": stock_code,
            "date": trade_date.isoformat(),
            "tick_count": len(response.data) if response.data else 0,
            "message": response.message
        }

    except Exception as e:
        logger.error(f"内部获取分笔数据失败 {stock_code}: {e}")
        return {
            "success": False,
            "stock_code": stock_code,
            "date": trade_date.isoformat(),
            "tick_count": 0,
            "message": f"获取失败: {str(e)}"
        }


@internal_router.get("/health")
async def tick_data_health_check(tongdaxin_client=Depends(get_tongdaxin_client)):
    """
    内部接口：分笔数据服务健康检查

    检查通达信连接状态和基本功能
    """
    try:
        status = await tongdaxin_client.get_status()

        # 基本健康检查
        health_info = {
            "status": "healthy" if status.is_connected else "unhealthy",
            "tongdaxin_connected": status.is_connected,
            "available_servers": len(status.available_servers),
            "response_time": status.response_time,
            "error_message": status.error_message,
            "timestamp": datetime.now().isoformat()
        }

        return health_info

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "error",
            "tongdaxin_connected": False,
            "available_servers": 0,
            "response_time": None,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }