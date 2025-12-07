"""
股票数据API路由
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Query, Path

from models.base_models import ApiResponse
from services.stock_data_service import StockDataService

logger = logging.getLogger(__name__)

# 创建路由器
stock_router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])

# 初始化股票数据服务
stock_service = StockDataService()


@stock_router.get("/{symbol}", response_model=None, summary="获取股票实时数据")
async def get_stock_data(symbol: str = Path(..., description="股票代码，如AAPL, TSLA, 000001等")):
    """
    获取指定股票的实时数据

    Args:
        symbol: 股票代码（支持A股代码如000001和国际股票如AAPL）

    Returns:
        股票实时价格和基本信息
    """
    try:
        # 使用真实的股票数据服务
        data = await stock_service.get_real_time_data(symbol)

        return ApiResponse(
            success=True,
            message=f"获取股票 {symbol} 数据成功",
            data=data
        )

    except Exception as e:
        logger.error(f"获取股票数据失败: {e}")
        return ApiResponse(
            success=False,
            message=f"获取股票数据失败: {str(e)}"
        )


@stock_router.get("/{symbol}/history", response_model=None, summary="获取股票历史数据")
async def get_stock_history(
    symbol: str = Path(..., description="股票代码"),
    period: str = Query("1mo", description="时间周期: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"),
    interval: str = Query("1d", description="数据间隔: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo")
):
    """
    获取指定股票的历史数据

    Args:
        symbol: 股票代码
        period: 时间周期
        interval: 数据间隔

    Returns:
        股票历史价格数据
    """
    try:
        # 使用真实的股票数据服务
        data = await stock_service.get_historical_data(symbol, period, interval)

        return ApiResponse(
            success=True,
            message=f"获取股票 {symbol} 历史数据成功",
            data=data
        )

    except Exception as e:
        logger.error(f"获取股票历史数据失败: {e}")
        return ApiResponse(
            success=False,
            message=f"获取股票历史数据失败: {str(e)}"
        )


@stock_router.get("/search/{query}", response_model=None, summary="搜索股票")
async def search_stocks(query: str = Path(..., description="搜索关键词")):
    """
    根据关键词搜索股票

    Args:
        query: 搜索关键词（公司名或股票代码）

    Returns:
        匹配的股票列表
    """
    try:
        # 使用真实的股票数据服务
        data = await stock_service.search_stocks(query)

        return ApiResponse(
            success=True,
            message=f"搜索股票 '{query}' 成功",
            data=data
        )

    except Exception as e:
        logger.error(f"搜索股票失败: {e}")
        return ApiResponse(
            success=False,
            message=f"搜索股票失败: {str(e)}"
        )


@stock_router.get("/sources", response_model=None, summary="获取数据源信息")
async def get_data_sources():
    """
    获取可用的数据源信息

    Returns:
        数据源配置和状态
    """
    try:
        data = stock_service.get_available_data_sources()

        return ApiResponse(
            success=True,
            message="获取数据源信息成功",
            data=data
        )

    except Exception as e:
        logger.error(f"获取数据源信息失败: {e}")
        return ApiResponse(
            success=False,
            message=f"获取数据源信息失败: {str(e)}"
        )