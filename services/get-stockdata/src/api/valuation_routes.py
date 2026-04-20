# -*- coding: utf-8 -*-
"""
估值数据 API Routes - 直连 MySQL DAO 层
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Query
import logging

from data_access.mysql_pool import MySQLPoolManager
from data_access.valuation_dao import ValuationDAO

router = APIRouter(prefix="/api/v1/market/valuation", tags=["市场估值"])
logger = logging.getLogger(__name__)

# 获取 MySQL 连接池的依赖
async def get_mysql_pool():
    return MySQLPoolManager.get_pool()

@router.get("/{stock_code}")
async def get_current_valuation(
    stock_code: str = Path(..., description="股票代码"),
    pool = Depends(get_mysql_pool)
):
    """
    获取最新估值指标 (PE/PB/市值) - 直连 MySQL
    """
    try:
        data = await ValuationDAO().get_latest_valuation(pool, stock_code)
        if not data:
            raise HTTPException(
                status_code=404, 
                detail=f"No valuation data found for {stock_code}. 数据尚未同步或不存在。"
            )
            
        if 'code' in data:
            # 兼容老前端格式，提取6位代码
            parts = str(data['code']).split('.')
            data['code'] = parts[0]
            
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch valuation for {stock_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取估值数据失败: {str(e)}"
        )


@router.get("/{stock_code}/history")
async def get_valuation_history(
    stock_code: str = Path(..., description="股票代码"),
    limit: int = Query(30, description="获取的历史天数"),
    pool = Depends(get_mysql_pool)
):
    """
    获取历史估值走势与统计 - 直连 MySQL
    """
    try:
        data_list = await ValuationDAO().get_valuation_history(pool, stock_code, limit=limit)
        
        if not data_list:
            raise HTTPException(
                status_code=404,
                detail=f"No valuation history found for {stock_code}"
            )
        
        for item in data_list:
            if 'code' in item:
                parts = str(item['code']).split('.')
                item['code'] = parts[0]
                
        return {
            "code": stock_code,
            "data": data_list,
            "count": len(data_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch valuation history for {stock_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取估值历史数据失败: {str(e)}"
        )
