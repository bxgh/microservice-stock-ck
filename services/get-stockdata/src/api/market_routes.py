# -*- coding: utf-8 -*-
"""
市场与行业数据 API Routes - 直连 MySQL DAO 层
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Query
import logging

from data_access.mysql_pool import MySQLPoolManager
from data_access.market_data_dao import MarketDataDAO
from data_access.sector_dao import SectorDAO

router = APIRouter(prefix="/api/v1/market", tags=["市场与行业"])
logger = logging.getLogger(__name__)

async def get_mysql_pool():
    return MySQLPoolManager.get_pool()

@router.get("/sector/list")
async def get_sector_list(pool = Depends(get_mysql_pool)):
    """
    获取全量板块/行业列表 - 直连 MySQL
    """
    try:
        data_list = await SectorDAO().get_sector_list(pool)
        return {
            "success": True,
            "data": data_list,
            "count": len(data_list)
        }
    except Exception as e:
        logger.error(f"Error fetching sector list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching sector list: {str(e)}")

@router.get("/sector/{sector_code}/stocks")
async def get_sector_stocks(
    sector_code: str = Path(..., description="板块名称或完整名称(如 同花顺_半导体)"),
    pool = Depends(get_mysql_pool)
):
    """
    获取指定板块的成分股 - 直连 MySQL
    """
    try:
        from urllib.parse import unquote
        try:
            sector_name = unquote(sector_code)
        except:
            sector_name = sector_code

        data_list = await SectorDAO().get_sector_constituents(pool, sector_name)
        if not data_list:
            raise HTTPException(status_code=404, detail=f"No stocks found for sector {sector_name}")
            
        return {
            "success": True,
            "sector": sector_name,
            "data": data_list,
            "count": len(data_list)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching sector stocks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching sector stocks: {str(e)}")

@router.get("/dragon_tiger")
async def get_dragon_tiger(
    code: str = Query(..., description="股票代码"),
    start_date: str = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(None, description="结束日期 (YYYY-MM-DD)"),
    pool = Depends(get_mysql_pool)
):
    """
    获取龙虎榜历史数据 - 直连 MySQL
    注意: API 形态已根据 DAO 层调整，现在查询指定个股的龙虎榜
    """
    try:
        df = await MarketDataDAO().get_lhb_data(pool, code, start_date, end_date)
        if df.empty:
            return {"success": True, "data": [], "count": 0}
            
        data = df.to_dict(orient='records')
        # 兼容日期序列化
        for item in data:
            if 'trade_date' in item and item['trade_date']:
                item['trade_date'] = str(item['trade_date'])
                
        return {
            "success": True,
            "data": data,
            "count": len(data)
        }
    except Exception as e:
        logger.error(f"Error fetching dragon tiger data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching dragon tiger data: {str(e)}")

@router.get("/capital_flow/{stock_code}")
async def get_capital_flow(
    stock_code: str = Path(..., description="股票代码"),
    pool = Depends(get_mysql_pool)
):
    """
    获取资金流向 (此版本切替为获取北向资金流动历史) - 直连 MySQL
    """
    try:
        df = await MarketDataDAO().get_north_funds_data(pool, stock_code)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No north funds capital data for {stock_code}")
            
        data = df.to_dict(orient='records')
        for item in data:
            if 'trade_date' in item and item['trade_date']:
                item['trade_date'] = str(item['trade_date'])
                
        return {
            "success": True,
            "code": stock_code[:6],
            "data": data,
            "count": len(data)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching capital flow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching capital flow: {str(e)}")

@router.get("/ranking")
async def get_market_ranking(ranking_type: str = Query("limit_up")):
    """
    获取市场榜单数据 - 已废弃
    """
    raise HTTPException(status_code=410, detail="泛市场榜单实时计算功能已迁移至独立监控服务。")

@router.get("/industry/{industry_code}/stats")
async def get_industry_stats(industry_code: str):
    """兼容旧版本的行业统计接口 - 已废弃"""
    raise HTTPException(status_code=410, detail="基于宽泛行业维度的统计接口已废弃，推荐改用 /api/v1/market/sector/ 相关路由。")
