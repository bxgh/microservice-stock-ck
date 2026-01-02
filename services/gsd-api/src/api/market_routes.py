# -*- coding: utf-8 -*-
"""
市场与行业数据 API Routes - 通过 gRPC 调用 mootdx-source
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from urllib.parse import unquote
import pandas as pd
from typing import Dict, Any, List

from grpc_client import get_datasource_client, DataSourceClient

router = APIRouter(prefix="/api/v1/market", tags=["市场与行业"])

async def get_client() -> DataSourceClient:
    """Dependency to get DataSourceClient"""
    return await get_datasource_client()

@router.get("/ranking")
async def get_market_ranking(
    ranking_type: str = Query("limit_up", description="榜单类型: limit_up (涨停), hot (人气), up (涨幅), volume (成交量)"),
    client: DataSourceClient = Depends(get_client)
):
    """
    获取市场榜单数据 (人气、涨停等) - 用于 Smart Money 策略
    """
    try:
        # 汉字转拼音/标识符映射 (如果用户输入了汉字)
        mapping = {
            "人气": "hot",
            "涨幅": "up",
            "涨停": "limit_up",
            "成交量": "volume"
        }
        actual_type = mapping.get(ranking_type, ranking_type)
        
        df = await client.fetch_ranking(actual_type)
        
        if df.empty:
            return {"success": True, "data": [], "count": 0}
            
        data = df.where(pd.notnull(df), None).to_dict(orient='records')
        
        # 统一代码格式
        for item in data:
            if 'code' in item:
                item['code'] = str(item['code']).zfill(6)
                
        return {
            "success": True,
            "type": ranking_type,
            "data": data,
            "count": len(data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching ranking: {str(e)}")

@router.get("/sector/list")
async def get_sector_list(
    client: DataSourceClient = Depends(get_client)
):
    """
    获取全量板块/行业列表 (通过自然语言查询)
    """
    try:
        # 使用 DATA_TYPE_SECTOR 配合通用查询
        df = await client.fetch_sector("所有板块")
        
        if df.empty:
            return {"success": True, "data": [], "count": 0}
            
        return {
            "success": True,
            "data": df.where(pd.notnull(df), None).to_dict(orient='records'),
            "count": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sector list: {str(e)}")

@router.get("/sector/{sector_code}/stocks")
async def get_sector_stocks(
    sector_code: str = Path(..., description="板块代码或名称"),
    client: DataSourceClient = Depends(get_client)
):
    """
    获取指定板块的成分股
    """
    try:
        # 尝试解码
        try:
            sector_name = unquote(sector_code)
        except:
            sector_name = sector_code
            
        df = await client.fetch_sector(f"{sector_name}的成分股")
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No stocks found for sector {sector_code}")
            
        data = df.where(pd.notnull(df), None).to_dict(orient='records')
        for item in data:
            if 'code' in item:
                item['code'] = str(item['code']).zfill(6)
                
        return {
            "success": True,
            "sector": sector_name,
            "data": data,
            "count": len(data)
        }
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Error fetching sector stocks: {str(e)}")

# 保留原有的 industry 接口重定向
@router.get("/industry/{industry_code}/stats")
async def get_industry_stats(
    industry_code: str,
    client: DataSourceClient = Depends(get_client)
):
    """兼容旧版本的行业统计接口"""
    params = {"industry": industry_code}
    df = await client.fetch_ranking("industry_stats", params=params)
    if df.empty:
        return {"industry": industry_code, "stats": {}, "message": "No stats found"}
    return df.where(pd.notnull(df), None).to_dict(orient='records')
@router.get("/dragon_tiger")
async def get_dragon_tiger(
    date: str = Query(None, description="日期 (YYYY-MM-DD)"),
    client: DataSourceClient = Depends(get_client)
):
    """
    获取龙虎榜数据 - 识别主力投机动向
    """
    try:
        from datasource.v1 import data_source_pb2
        params = {}
        if date:
            params["date"] = date
            
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_META,
            params=params
        )
        # 路由到 META/DragonTiger
        df = await client.fetch_meta("")
        
        if df.empty:
            return {"success": True, "data": [], "count": 0}
            
        data = df.where(pd.notnull(df), None).to_dict(orient='records')
        for item in data:
            if 'code' in item:
                item['code'] = str(item['code']).zfill(6)
                
        return {
            "success": True,
            "data": data,
            "count": len(data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dragon tiger data: {str(e)}")

@router.get("/capital_flow/{stock_code}")
async def get_capital_flow(
    stock_code: str = Path(..., description="股票代码"),
    client: DataSourceClient = Depends(get_client)
):
    """
    获取个股资金流向 - Smart Money 策略核心
    """
    try:
        df = await client.fetch_ranking("capital_flow", params={"code": stock_code})
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No capital flow data for {stock_code}")
            
        return {
            "success": True,
            "code": stock_code.zfill(6),
            "data": df.where(pd.notnull(df), None).to_dict(orient='records')[0]
        }
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Error fetching capital flow: {str(e)}")
