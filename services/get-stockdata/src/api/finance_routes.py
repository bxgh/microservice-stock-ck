# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, List
import pandas as pd

from grpc_client import get_datasource_client, DataSourceClient

router = APIRouter(prefix="/api/v1/finance", tags=["财务数据"])

async def get_client() -> DataSourceClient:
    """Dependency to get DataSourceClient"""
    return await get_datasource_client()

@router.get("/indicators/{stock_code}")
async def get_enhanced_indicators(
    stock_code: str,
    client: DataSourceClient = Depends(get_client)
):
    """
    获取增强财务指标 - 通过 gRPC
    """
    try:
        df = await client.fetch_finance(stock_code)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No financial data found for {stock_code}")
        
        # 处理 NaN 为 None (JSON 兼容)
        data_list = df.where(pd.notnull(df), None).to_dict(orient='records')
        return data_list[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error fetching financial indicators: {str(e)}")

@router.get("/history/{stock_code}")
async def get_financial_history(
    stock_code: str,
    periods: int = Query(8, ge=1, le=20, description="历史期数"),
    report_type: str = Query("Q", description="报告类型 (Q=季报, A=年报)"),
    client: DataSourceClient = Depends(get_client)
):
    """
    获取历史财务数据 - 通过 gRPC
    """
    try:
        params = {"periods": str(periods), "report_type": report_type}
        df = await client.fetch_finance(stock_code, params=params)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No financial history found for {stock_code}")
            
        # 处理 NaN 为 None (JSON 兼容)
        data_list = df.where(pd.notnull(df), None).to_dict(orient='records')
        return {
            "stock_code": stock_code,
            "data": data_list
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error fetching financial history: {str(e)}")
