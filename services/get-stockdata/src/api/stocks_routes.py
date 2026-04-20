# -*- coding: utf-8 -*-
"""
股票基本信息 API Routes - 直连 MySQL DAO 层
"""
from fastapi import APIRouter, HTTPException, Depends, Path
import logging

from data_access.mysql_pool import MySQLPoolManager
from data_access.stock_basic_dao import StockBasicDAO

router = APIRouter(prefix="/api/v1/stocks", tags=["股票信息"])
logger = logging.getLogger(__name__)

async def get_mysql_pool():
    return MySQLPoolManager.get_pool()

@router.get("/list")
async def list_stocks(pool = Depends(get_mysql_pool)):
    """
    获取所有股票列表 - 直连 MySQL
    """
    try:
        data_list = await StockBasicDAO().get_stock_list(pool)
        return {
            "success": True,
            "data": data_list,
            "count": len(data_list)
        }
    except Exception as e:
        logger.error(f"Error listing stocks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing stocks: {str(e)}")

@router.get("/{stock_code}/info")
async def get_stock_info(
    stock_code: str = Path(..., description="股票代码"),
    pool = Depends(get_mysql_pool)
):
    """
    获取股票基本信息 (代码、名称、行业、上市日期等) - 直连 MySQL
    """
    try:
        data = await StockBasicDAO().get_stock_info(pool, stock_code)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No info found for stock {stock_code}")
            
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stock info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching stock info: {str(e)}")
