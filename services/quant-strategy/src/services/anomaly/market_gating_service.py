import logging
from datetime import date
from typing import Dict, Any, Tuple

from adapters.stock_data_provider import data_provider

logger = logging.getLogger("MarketGatingService")

class MarketGatingService:
    """
    市场门控服务 (E4)
    负责识别极端市况并决定推送策略
    """
    
    def __init__(self, limit_threshold: int = 100):
        self.limit_threshold = limit_threshold
        self.initialized = False

    async def initialize(self):
        """初始化"""
        if not self.initialized:
            # 可以从配置或数据库加载动态阈值
            self.initialized = True
            logger.info(f"MarketGatingService initialized with limit_threshold={self.limit_threshold}")

    async def check_extreme_market(self, target_date: date) -> Tuple[bool, str]:
        """
        检查是否属于极端市况 (普涨/普跌)
        阈值：涨停或跌停数 > limit_threshold
        
        Returns:
            Tuple[bool, str]: (是否极端, 原因描述)
        """
        if not self.initialized:
            await self.initialize()

        breadth = await data_provider.get_market_breadth(target_date)
        
        if not breadth:
            logger.warning(f"No market breadth data found for {target_date}, assuming normal.")
            return False, "No Data"

        limit_up = breadth.get("limit_up_count", 0)
        limit_down = breadth.get("limit_down_count", 0)
        
        logger.info(f"Market Breadth for {target_date}: LimitUp={limit_up}, LimitDown={limit_down}")

        if limit_up > self.limit_threshold:
            return True, f"Extreme Bullish (Limit Up: {limit_up})"
        
        if limit_down > self.limit_threshold:
            return True, f"Extreme Bearish (Limit Down: {limit_down})"
            
        return False, "Normal"

# 全局单例
market_gating_service = MarketGatingService()
