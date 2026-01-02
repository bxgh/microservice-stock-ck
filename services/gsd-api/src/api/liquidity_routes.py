# -*- coding: utf-8 -*-
"""
流动性数据 API Routes - 通过 gRPC 调用 mootdx-source
"""
from fastapi import APIRouter, HTTPException, Depends, Path
from typing import Dict, Any
import logging

from grpc_client import get_datasource_client, DataSourceClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stocks", tags=["流动性"])


async def get_client() -> DataSourceClient:
    """Dependency to get DataSourceClient"""
    return await get_datasource_client()


@router.get("/{stock_code}/liquidity")
async def get_liquidity_metrics(
    stock_code: str = Path(..., description="股票代码"),
    client: DataSourceClient = Depends(get_client)
) -> Dict[str, Any]:
    """
    获取流动性指标
    
    包括：买卖盘口、成交量、换手率等
    
    通过实时行情数据计算流动性指标
    """
    try:
        # 获取实时行情数据
        df = await client.fetch_quotes([stock_code])
        
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"未找到股票 {stock_code} 的数据"
            )
        
        quote = df.to_dict(orient='records')[0]
        
        # 提取流动性相关指标
        liquidity_metrics = {
            "code": stock_code,
            "volume": quote.get("volume", 0),
            "turnover": quote.get("turnover", 0),
            "turnover_ratio": quote.get("turnover_ratio", 0),
            "bid_ask_spread": None,  # 需要5档数据
            "market_depth": None,    # 需要5档数据
            "timestamp": quote.get("timestamp")
        }
        
        return liquidity_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching liquidity metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取流动性指标失败: {str(e)}"
        )
