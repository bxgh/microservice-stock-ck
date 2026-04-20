# -*- coding: utf-8 -*-
"""
财务数据 API Routes - 直连 MySQL DAO 层
"""
from fastapi import APIRouter, HTTPException, Query, Depends
import logging

from data_access.mysql_pool import MySQLPoolManager
from data_access.finance_dao import FinanceDAO

router = APIRouter(prefix="/api/v1/finance", tags=["财务数据"])
logger = logging.getLogger(__name__)

async def get_mysql_pool():
    return MySQLPoolManager.get_pool()

@router.get("/indicators/{stock_code}")
async def get_enhanced_indicators(
    stock_code: str,
    pool = Depends(get_mysql_pool)
):
    """
    获取增强/衍生财务指标 (ROE/毛利率等) - 直连 MySQL
    """
    try:
        # 使用最新封装的衍生指标获取方法
        data = await FinanceDAO().get_derived_indicators(pool, stock_code)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No financial indicators found for {stock_code}. 数据可能尚未同步。")
        
        # Format dates if present
        if 'report_date' in data and data['report_date']:
            data['report_date'] = str(data['report_date'])
        if 'updated_at' in data and data['updated_at']:
            data['updated_at'] = str(data['updated_at'])
            
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching financial indicators: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching financial indicators: {str(e)}")

@router.get("/history/{stock_code}")
async def get_financial_history(
    stock_code: str,
    periods: int = Query(8, ge=1, le=20, description="历史期数"),
    report_type: str = Query("Q", description="报告类型 (Q=季报, A=年报) - 目前暂仅供展示使用，DAO底层根据日期返回所有季报/年报"),
    pool = Depends(get_mysql_pool)
):
    """
    获取历史财务数据 (三大报表聚合快照) - 直连 MySQL
    """
    try:
        data_list = await FinanceDAO().get_financial_history(pool, stock_code, limit=periods)
        
        if not data_list:
            raise HTTPException(status_code=404, detail=f"No financial history found for {stock_code}")
            
        # Format dates
        for item in data_list:
            if 'report_date' in item and item['report_date']:
                item['report_date'] = str(item['report_date'])
            if 'announce_date' in item and item['announce_date']:
                item['announce_date'] = str(item['announce_date'])
                
        return {
            "stock_code": stock_code,
            "data": data_list
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching financial history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching financial history: {str(e)}")
