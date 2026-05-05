# -*- coding: utf-8 -*-
"""
估值数据 API Routes - 通过 gRPC 调用 mootdx-source
"""
from fastapi import APIRouter, HTTPException, Depends, Path
from typing import Dict, Any, List
import logging
import pandas as pd

from grpc_client import get_datasource_client, DataSourceClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/market/valuation", tags=["市场估值"])


async def get_client() -> DataSourceClient:
    """Dependency to get DataSourceClient"""
    return await get_datasource_client()


@router.get("/{stock_code}")
async def get_current_valuation(
    stock_code: str = Path(..., description="股票代码"),
    client: DataSourceClient = Depends(get_client)
) -> Dict[str, Any]:
    """
    获取实时估值指标 (PE/PB/市值) - 通过 gRPC
    """
    try:
        df = await client.fetch_valuation(stock_code)
        
        if df.empty:
            raise HTTPException(
                status_code=404, 
                detail=f"No valuation data found for {stock_code}"
            )
        
        # 处理 NaN 为 None (JSON 兼容)
        # Using a more robust replacement for various types of nulls
        df = df.replace({float('nan'): None, pd.NA: None})
        data_list = df.where(pd.notnull(df), None).to_dict(orient='records')
        if not data_list:
            raise HTTPException(status_code=404, detail=f"No valuation data found for {stock_code}")
            
        data = data_list[0]
        if 'code' in data:
            data['code'] = str(data['code']).zfill(6)
            
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching current valuation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取估值数据失败: {str(e)}"
        )


@router.get("/{stock_code}/history")
async def get_valuation_history(
    stock_code: str = Path(..., description="股票代码"),
    client: DataSourceClient = Depends(get_client)
) -> Dict[str, Any]:
    """
    获取历史估值走势与统计
    """
    try:
        df = await client.fetch_valuation(stock_code)
        
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No valuation history found for {stock_code}"
            )
        
        # 处理 NaN 为 None (JSON 兼容)
        data_list = df.where(pd.notnull(df), None).to_dict(orient='records')
        for item in data_list:
            if 'code' in item:
                item['code'] = str(item['code']).zfill(6)
                
        return {
            "code": stock_code,
            "data": data_list,
            "count": len(data_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching valuation history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取估值历史数据失败: {str(e)}"
        )
