# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Query, Depends, Path
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
import logging
import os

from grpc_client import get_datasource_client, DataSourceClient
from data_access import MySQLPoolManager, KLineDAO

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/quotes", tags=["行情数据"])



async def get_client() -> DataSourceClient:
    """Dependency to get DataSourceClient"""
    return await get_datasource_client()

@router.get("/realtime")
async def get_realtime_quotes(
    codes: str = Query(..., description="股票代码列表，逗号分隔 (e.g. 600519,000001)"),
    client: DataSourceClient = Depends(get_client)
):
    """
    批量获取实时行情 - 通过 gRPC 调用 mootdx-source
    """
    try:
        code_list = [c.strip() for c in codes.split(',') if c.strip()]
        if not code_list:
            return {"success": True, "data": [], "count": 0}
        
        df = await client.fetch_quotes(code_list)
        
        if df.empty:
            return {"success": True, "data": [], "count": 0}
            
        # 处理 NaN 为 None (JSON 兼容)
        quotes = df.where(pd.notnull(df), None).to_dict(orient='records')
        
        # 统一代码格式
        for q in quotes:
            if 'code' in q:
                q['code'] = str(q['code']).zfill(6)
            
        return {
            "success": True,
            "data": quotes,
            "count": len(quotes)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quotes: {str(e)}")

@router.get("/tick/{stock_code}")
async def get_tick_data(
    stock_code: str = Path(..., description="股票代码"),
    date: str = Query(None, description="日期 (YYYYMMDD)，不填默认为当日"),
    client: DataSourceClient = Depends(get_client)
):
    """
    获取分笔数据 - 用于 OFI 策略
    """
    try:
        if not date:
            date = datetime.now().strftime("%Y%m%d")
            
        df = await client.fetch_tick(stock_code, date)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No tick data found for {stock_code} on {date}")
            
        data = df.where(pd.notnull(df), None).to_dict(orient='records')
        
        # 统一代码格式
        for item in data:
            if 'code' in item:
                item['code'] = str(item['code']).zfill(6)
            else:
                item['code'] = stock_code.zfill(6)
        
        return {
            "success": True,
            "code": stock_code.zfill(6),
            "date": date,
            "data": data,
            "count": len(data)
        }
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Error fetching tick data: {str(e)}")

@router.get("/history/{stock_code}")
async def get_historical_kline(
    stock_code: str = Path(..., description="股票代码"),
    start_date: str = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(None, description="结束日期 (YYYY-MM-DD)"),
    frequency: str = Query("d", description="频率: d=日, w=周, m=月, 1m, 5m, 15m, 30m, 60m"),
    adjust: str = Query("2", description="复权: 0=不复权, 1=前复权, 2=后复权")
):
    """
    获取历史 K 线数据 - 优先从ClickHouse查询，失败时降级到MySQL
    
    注意: 目前只支持日线数据（frequency=d），其他频率参数将被忽略
    """
    try:
        if not start_date:
            from datetime import timedelta
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        df = pd.DataFrame()
        data_source = "Unknown"
        
        # 尝试1: 从ClickHouse查询（本地快速查询）
        try:
            from data_access import ClickHousePoolManager, ClickHouseKLineDAO
            
            pool = await ClickHousePoolManager.get_pool()
            ch_dao = ClickHouseKLineDAO()
            
            df = await ch_dao.get_kline_data(
                pool=pool,
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjust=adjust
            )
            
            if not df.empty:
                data_source = "ClickHouse (Local)"
                logger.info(f"✓ 从ClickHouse获取K线数据: {stock_code}")
            else:
                logger.info(f"ClickHouse无数据，尝试MySQL fallback: {stock_code}")
                
        except Exception as e:
            logger.warning(f"ClickHouse查询失败，降级到MySQL: {e}")
        
        # 尝试2: 从MySQL查询（云端备份）
        if df.empty:
            try:
                pool = await MySQLPoolManager.get_pool()
                mysql_dao = KLineDAO()
                df = await mysql_dao.get_kline_data(
                    pool=pool,
                    stock_code=stock_code,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency,
                    adjust=adjust
                )
                
                if not df.empty:
                    data_source = "Tencent Cloud MySQL (Fallback)"
                    logger.info(f"✓ 从MySQL获取K线数据: {stock_code}")
                    
            except Exception as e:
                logger.error(f"MySQL查询也失败: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to fetch data from both ClickHouse and MySQL: {str(e)}")
        
        # 数据验证
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No historical data found for {stock_code}")
            
        data = df.where(pd.notnull(df), None).to_dict(orient='records')
        
        # 统一代码格式
        for item in data:
            if 'stock_code' in item:
                item['code'] = str(item['stock_code']).zfill(6)
                del item['stock_code']
            elif 'code' not in item:
                item['code'] = stock_code.zfill(6)
                
        return {
            "success": True,
            "code": stock_code.zfill(6),
            "frequency": frequency,
            "data": data,
            "count": len(data),
            "source": data_source
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching historical data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching historical data: {str(e)}")
