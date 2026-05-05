import logging
from datetime import datetime
import pandas as pd
from typing import Tuple

from src.strategies.geopolitical.constants import (
    ScenarioType, 
    WAR_START_DATE, 
    BASE_INDEX, 
    BASE_OIL,
    THRESHOLD_DAYS_A_B,
    THRESHOLD_DAYS_B_C,
    TRIGGER_INDEX_DROP,
    TRIGGER_OIL_SURGE
)
from src.dao.kline import KLineDAO
from src.dao.futures import futures_dao

logger = logging.getLogger(__name__)

class ScenarioDetector:
    """
    地缘冲突情景检测器
    负责根据时间、大盘跌幅和原油涨幅确定当前的判定情景。
    """

    def __init__(self):
        self.kline_dao = KLineDAO()
        self.futures_dao = futures_dao

    async def get_market_changes(self, current_date: str) -> Tuple[float, float]:
        """
        获取从战争起始日至今的大盘跌幅和原油涨幅
        """
        # 转换日期格式
        start_dt = WAR_START_DATE
        end_dt = current_date

        # 1. 获取基准指数 (沪深300) 数据
        # 我们需要起始日（或其前一天）的收盘价和当前的收盘价
        # 起始日 2026-03-01 的基准通常取前一交易日收盘
        index_df = await self.kline_dao.get_kline([BASE_INDEX], "2026-02-01", end_dt)
        
        # 2. 获取原油价格数据
        oil_df = await self.futures_dao.get_futures_kline(BASE_OIL, "2026-02-01", end_dt)

        index_change = 0.0
        oil_change = 0.0

        if not index_df.empty:
            # 确保 trade_date 是日期类型方便对比
            index_df['trade_date'] = pd.to_datetime(index_df['trade_date']).dt.date
            # 找到最接近 WAR_START_DATE 之前的价格作为基准价
            pre_war_index = index_df[index_df['trade_date'] < pd.to_datetime(WAR_START_DATE).date()]
            if not pre_war_index.empty:
                base_price = pre_war_index.iloc[-1]['close']
                curr_price = index_df.iloc[-1]['close']
                index_change = (curr_price - base_price) / base_price
        
        if not oil_df.empty:
            # 确保 trade_date 是日期类型方便对比
            oil_df['trade_date'] = pd.to_datetime(oil_df['trade_date']).dt.date
            pre_war_oil = oil_df[oil_df['trade_date'] < pd.to_datetime(WAR_START_DATE).date()]
            if not pre_war_oil.empty:
                base_price = pre_war_oil.iloc[-1]['close_price']
                curr_price = oil_df.iloc[-1]['close_price']
                oil_change = (curr_price - base_price) / base_price

        return index_change, oil_change

    async def detect_scenario(self, current_date: str) -> ScenarioType:
        """
        根据日期和市场状态判定情景
        """
        target_date = pd.to_datetime(current_date)
        start_date = pd.to_datetime(WAR_START_DATE)
        
        if target_date < start_date:
            return ScenarioType.IDLE

        duration = (target_date - start_date).days
        
        # 获取市场波动数据
        idx_change, oil_change = await self.get_market_changes(current_date)
        
        logger.info(f"Scenario Detection for {current_date}: Duration={duration}d, IndexChange={idx_change:.2%}, OilChange={oil_change:.2%}")

        # 持久战判定 (C): 时间超过 90 天
        if duration > THRESHOLD_DAYS_B_C:
            return ScenarioType.SCENARIO_C

        # 中度冲突判定 (B): 时间在 14~90 天之间
        if duration > THRESHOLD_DAYS_A_B:
            return ScenarioType.SCENARIO_B

        # 闪电战/初期判定 (A): 
        # 如果还在前14天内，且满足触发条件，则为 A
        # 如果没满足剧烈波动阈值，可能仍处于观察 IDLE 或弱 A (本策略严格按照逻辑定为 A)
        return ScenarioType.SCENARIO_A

# 单例
scenario_detector = ScenarioDetector()
