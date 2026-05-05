import logging
import asyncio
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime, timedelta

from src.analyzers.geopolitical_analyzer import GeopoliticalAnalyzer
from src.dao.kline import KLineDAO
from src.strategies.geopolitical.constants import WAR_START_DATE, BASE_INDEX

logger = logging.getLogger(__name__)

class DefenseFactorService:
    """
    防御因子计算服务
    负责批量计算股票在战争期间的各项防御性指标。
    """

    def __init__(self, kline_dao=None, analyzer=None):
        self.kline_dao = kline_dao or KLineDAO()
        self.analyzer = analyzer or GeopoliticalAnalyzer()

    async def compute_factors(
        self, 
        stock_codes: List[str], 
        current_date: str
    ) -> pd.DataFrame:
        """
        批量计算防御性特征指标
        
        Args:
            stock_codes: 股票代码列表
            current_date: 当前业务日期 (YYYY-MM-DD)
            
        Returns:
            pd.DataFrame: 包含 code, excess_return, max_drawdown, volume_ratio
        """
        if not stock_codes:
            return pd.DataFrame()

        # 1. 获取基础数据区间
        # 战争期间: WAR_START_DATE -> current_date
        # 战前期 (用于计算成交量基准): WAR_START_DATE 前 30 天
        start_dt = WAR_START_DATE
        end_dt = current_date
        pre_war_start = (pd.to_datetime(start_dt) - timedelta(days=40)).strftime("%Y-%m-%d")

        logger.info(f"Computing defense factors for {len(stock_codes)} stocks up to {current_date}")

        # 2. 获取基准指数数据
        index_df = await self.kline_dao.get_kline([BASE_INDEX], start_dt, end_dt)
        
        # 3. 批量获取个股数据 (此处 KLineDAO 需要支持批量，如果不提供则循环获取)
        # 考虑到大量股票，使用信号量控制并发
        semaphore = asyncio.Semaphore(10)
        results = []

        async def process_single_stock(code):
            async with semaphore:
                try:
                    # 获取 full_df (包含战前期和战争期)
                    full_df = await self.kline_dao.get_kline([code], pre_war_start, end_dt)
                    if full_df.empty:
                        return None
                    
                    # 划分数据
                    full_df['trade_date'] = pd.to_datetime(full_df['trade_date']).dt.date
                    war_start_date_obj = pd.to_datetime(start_dt).date()
                    
                    pre_war_df = full_df[full_df['trade_date'] < war_start_date_obj]
                    war_period_df = full_df[full_df['trade_date'] >= war_start_date_obj]
                    
                    if war_period_df.empty:
                        return None

                    # 计算战前平均成交量 (取最近20个交易日)
                    pre_war_avg_vol = 0.0
                    if not pre_war_df.empty:
                        pre_war_avg_vol = pre_war_df.iloc[-20:]['volume'].mean()
                    
                    # 分析指标
                    metrics = self.analyzer.compute_all_metrics(
                        war_period_df, index_df, pre_war_avg_vol
                    )
                    metrics['code'] = code
                    return metrics
                except Exception as e:
                    logger.error(f"Error computing factors for {code}: {e}")
                    return None

        # 分批处理，避免一次性创建过万个任务导致 gRPC 超时
        batch_size = 50
        computed_results = []
        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(stock_codes)-1)//batch_size + 1} ({len(batch)} stocks)")
            batch_tasks = [process_single_stock(code) for code in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            computed_results.extend(batch_results)
        
        # 汇总结果
        valid_results = [r for r in computed_results if r]
        if not valid_results:
            return pd.DataFrame(columns=['code', 'excess_return', 'max_drawdown', 'volume_ratio'])

        return pd.DataFrame(valid_results)

# 单例
defense_factor_service = DefenseFactorService()
