import asyncio
import logging
from datetime import date
from typing import Dict, Any, List

from database.session import get_session
from database.anomaly_models import MarketBriefModel
from adapters.stock_data_provider import data_provider
from sqlalchemy.dialects.mysql import insert

logger = logging.getLogger("MarketBriefService")

class MarketBriefService:
    """
    D 视图 (市场全景简报) 生成服务 (E4-S3)
    """
    
    def __init__(self):
        self.initialized = False

    async def initialize(self):
        if not self.initialized:
            self.initialized = True

    async def generate_market_brief(self, target_date: date) -> Dict[str, Any]:
        """
        聚合多源数据生成市场全景简报
        """
        logger.info(f"Generating Market Brief for {target_date}...")
        
        # 1. 获取市场宽度 (ods_market_breadth_daily)
        breadth = await data_provider.get_market_breadth(target_date)
        
        # 2. 获取连板梯队 (ods_event_limit_pool)
        # 这里需要从数据库直接拉取当日所有 zt/lian 标的
        ladder = await self._calculate_limit_ladder(target_date)
        
        # 3. 获取行业排名 (ads_l2_industry_daily) - 待实现/简化
        # 目前先只做全景和梯队
        
        panorama_data = {
            "breadth": breadth,
            "market_status": "Extreme" if (breadth.get("limit_up_count", 0) > 100 or breadth.get("limit_down_count", 0) > 100) else "Normal"
        }
        
        brief = {
            "trade_date": target_date,
            "panorama_data": panorama_data,
            "ladder_data": ladder
        }
        
        # 4. 保存到数据库
        await self._save_brief(brief)
        
        return brief

    async def _calculate_limit_ladder(self, target_date: date) -> Dict[str, int]:
        """
        从数据库计算连板梯队
        """
        async with self._db_lock if hasattr(self, '_db_lock') else asyncio.Lock():
            async for session in get_session():
                from database.ods_models import EventLimitPoolModel
                from sqlalchemy import select, func

                stmt = select(
                    EventLimitPoolModel.board_height, 
                    func.count(EventLimitPoolModel.ts_code)
                ).where(
                    EventLimitPoolModel.trade_date == target_date,
                    EventLimitPoolModel.pool_type.in_(["zt", "lian"]),
                    EventLimitPoolModel.is_deleted == 0
                ).group_by(EventLimitPoolModel.board_height)
                
                res = await session.execute(stmt)
                ladder = {str(row[0]): row[1] for row in res.all()}
                return ladder

    async def _save_brief(self, brief: Dict[str, Any]):
        """
        保存简报到 MySQL
        """
        async for session in get_session():
            try:
                stmt = insert(MarketBriefModel).values(
                    trade_date=brief["trade_date"],
                    panorama_data=brief["panorama_data"],
                    ladder_data=brief["ladder_data"]
                )
                
                update_stmt = stmt.on_duplicate_key_update(
                    panorama_data=stmt.inserted.panorama_data,
                    ladder_data=stmt.inserted.ladder_data
                )
                
                await session.execute(update_stmt)
                await session.commit()
                logger.info(f"Saved market brief for {brief['trade_date']}")
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save market brief: {e}")
                raise

# 全局单例
market_brief_service = MarketBriefService()
