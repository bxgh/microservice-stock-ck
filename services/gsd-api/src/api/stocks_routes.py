# -*- coding: utf-8 -*-
"""
股票基本信息 API Routes - 通过 gRPC 调用 mootdx-source
"""
from fastapi import APIRouter, HTTPException, Depends, Path
import logging
import pandas as pd
from typing import Dict, Any

from grpc_client import get_datasource_client, DataSourceClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stocks", tags=["股票信息"])

async def get_client() -> DataSourceClient:
    """Dependency to get DataSourceClient"""
    return await get_datasource_client()

@router.get("/{stock_code}/info")
async def get_stock_info(
    stock_code: str = Path(..., description="股票代码"),
    client: DataSourceClient = Depends(get_client)
) -> Dict[str, Any]:
    """
    获取股票基本信息 (代码、名称、行业、上市日期等)
    """
    try:
        # 使用 DATA_TYPE_META 获取元数据
        # DataSourceClient 中需要支持 fetch_meta，如果没有则通过 fetch_ranking 模拟或添加
        # 暂时使用通用方式
        from datasource.v1 import data_source_pb2
        
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_META,
            codes=[stock_code]
        )
        
        # 直接调用 stub 或者在 client 中添加方法
        # 为了保持一致性，我们在 client.py 中添加 fetch_meta 方法
        df = await client.fetch_meta(stock_code)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No info found for stock {stock_code}")
            
        data = df.where(pd.notnull(df), None).to_dict(orient='records')[0]
        
        # 确保 code 格式
        if 'code' in data:
            data['code'] = str(data['code']).zfill(6)
        else:
            data['code'] = stock_code.zfill(6)
            
        return data
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error fetching stock info: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching stock info: {str(e)}")

@router.get("/list")
async def list_stocks(
    client: DataSourceClient = Depends(get_client)
) -> Dict[str, Any]:
    """
    获取所有股票列表
    """
    try:
        # 获取所有代码的元数据
        df = await client.fetch_meta("all")
        
        if df.empty:
            return {"success": True, "data": [], "count": 0}
            
        data_list = df.where(pd.notnull(df), None).to_dict(orient='records')
        
        for item in data_list:
            if 'code' in item:
                item['code'] = str(item['code']).zfill(6)
                
        return {
            "success": True,
            "data": data_list,
            "count": len(data_list)
        }
    except Exception as e:
        logger.error(f"Error listing stocks: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing stocks: {str(e)}")
