# -*- coding: utf-8 -*-
"""
EPIC-002 Market Valuation Service
Provides real-time and historical valuation metrics (PE, PB, Market Cap etc).
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from .cache_manager import CacheManager
from .time_aware_strategy import get_time_strategy
from data_sources.providers.akshare_provider import AkshareProvider
from data_sources.providers.base import DataType
from storage.clickhouse_writer import ClickHouseWriter, ValuationData
import time

try:
    from api.routers.metrics import record_data_source_request
except ImportError:
    def record_data_source_request(source, success, duration):
        pass

logger = logging.getLogger(__name__)

class ValuationService:
    """Market Valuation Service
    
    Provides:
    1. Real-time valuation (PE/PB/Market Cap)
    2. Historical valuation statistics (Percentiles, Trends)
    """
    
    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        enable_cache: bool = True,
        timeout: int = 45,
        clickhouse_writer: Optional[ClickHouseWriter] = None,
    ):
        self._cache_manager = cache_manager
        self._enable_cache = enable_cache
        self._timeout = timeout
        
        self._initialized = False
        self._lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
        
        # Use Remote Provider
        self._provider = AkshareProvider()
        self._clickhouse_writer = clickhouse_writer
        
        self._stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'akshare_calls': 0,
            'errors': 0,
        }

    async def initialize(self) -> bool:
        async with self._lock:
            if self._initialized:
                return True
            
            logger.info("Initializing ValuationService...")
            if self._enable_cache:
                if self._cache_manager is None:
                    self._cache_manager = CacheManager()
                if not await self._cache_manager.initialize():
                    logger.warning("CacheManager init failed, caching disabled")
                    self._enable_cache = False
            
            # Initialize Provider
            await self._provider.initialize()
            
            self._initialized = True
            logger.info("✅ ValuationService initialized (Remote Provider)")
            return True

    async def close(self) -> None:
        if self._cache_manager:
            await self._cache_manager.close()
        if self._provider:
            await self._provider.close()
        self._initialized = False
        logger.info("ValuationService closed")

    async def _ensure_initialized(self) -> bool:
        if not self._initialized:
            return await self.initialize()
        return True

    # _call_akshare removed, using self._provider instead

    async def get_current_valuation(self, stock_code: str) -> Dict[str, Any]:
        """获取实时估值指标 (EPIC-002)
        
        使用云端 AkShare API 获取实时 PE/PB/市值等数据
        """
        if not await self._ensure_initialized():
            raise RuntimeError("ValuationService not initialized")

        async with self._stats_lock:
            self._stats['total_requests'] += 1

        cache_key = f"valuation:current:{stock_code}"
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            async with self._stats_lock:
                self._stats['cache_misses'] += 1

        # 调用云端 API (通过 Provider)
        start_time = time.time()
        success = False
        try:
            res = await self._provider.fetch(DataType.VALUATION, symbol=stock_code)
            
            if not res.success or res.data.empty:
                logger.warning(f"Failed to fetch valuation from cloud for {stock_code}")
                return {}
            success = True
        finally:
            duration = time.time() - start_time
            record_data_source_request("cloud_akshare_valuation", success, duration)
            
        data = res.data.iloc[0].to_dict()
        
        # 单位转换常量 (元 -> 亿元)
        YUAN_TO_YI = 100_000_000
        
        def safe_float(val):
            try:
                if val is None or (isinstance(val, float) and np.isnan(val)):
                    return None
                return round(float(val), 4)
            except:
                return None

        result = {
            'stock_code': stock_code,
            'report_date': datetime.now().strftime('%Y%m%d'),
            'total_market_cap': safe_float(data.get('market_cap', 0) / YUAN_TO_YI) if data.get('market_cap') else None,
            'circulating_market_cap': None, # 云端暂未提供
            'pe_ttm': safe_float(data.get('pe')),
            'pe_static': None,
            'pb_ratio': safe_float(data.get('pb')),
            'ps_ratio': safe_float(data.get('ps')), 
            'pcf_ratio': None,
            'dividend_yield_ttm': safe_float(data.get('dividend_yield'))
        }
        
        # 写入 ClickHouse (Story 9.2)
        if self._clickhouse_writer and result:
            try:
                trade_date = datetime.now() # Use now for real-time
                v_data = ValuationData(
                    stock_code=stock_code,
                    trade_date=trade_date,
                    total_market_cap=result.get('total_market_cap') or 0.0,
                    circulating_market_cap=result.get('circulating_market_cap') or 0.0,
                    pe_ttm=result.get('pe_ttm') or 0.0,
                    pe_static=result.get('pe_static') or 0.0,
                    pb_ratio=result.get('pb_ratio') or 0.0,
                    ps_ratio=result.get('ps_ratio') or 0.0,
                    pcf_ratio=result.get('pcf_ratio') or 0.0,
                    dividend_yield_ttm=result.get('dividend_yield_ttm') or 0.0
                )
                await self._clickhouse_writer.write_valuation([v_data])
            except Exception as e:
                logger.error(f"Failed to write valuation to ClickHouse: {e}")

        # 缓存 (时段感知 TTL)
        if self._enable_cache and result:
            await self._cache_manager.set(cache_key, result, ttl=300) 
            
        return result

    async def get_valuation_history(
        self, 
        stock_code: str, 
        years: int = 5,
        frequency: str = 'D'
    ) -> Dict[str, Any]:
        """Get historical valuation via Remote API (Baidu)"""
        if not await self._ensure_initialized():
             raise RuntimeError("ValuationService not initialized")

        cache_key = f"valuation:history:{stock_code}:{years}:{frequency}"
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached:
                return cached

        # Use Provider to fetch history from Baidu (Robust)
        # Needs separate calls for PE / PB then merge
        
        async def fetch_series(indicator, col_name):
            res = await self._provider.fetch(DataType.VALUATION_BAIDU, symbol=stock_code, indicator=indicator)
            if res.success and not res.data.empty:
                df = res.data
                # Rename 'value' to col_name
                # Ensure date exists
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                elif '日期' in df.columns:
                     df['date'] = pd.to_datetime(df['日期'])
                
                if 'date' in df.columns:
                    df = df.set_index('date')
                    if 'value' in df.columns:
                        df = df.rename(columns={'value': col_name})
                        return df[[col_name]]
            return pd.DataFrame()

        pe_df, pb_df = await asyncio.gather(
            fetch_series("市盈率(TTM)", "pe_ttm"),
            fetch_series("市净率", "pb")
        )
        
        # Merge
        if pe_df.empty and pb_df.empty:
            return {}
            
        # Outer join on date index
        df = pe_df.join(pb_df, how='outer').sort_index()

        # Filter last N years
        cutoff_date = pd.Timestamp.now() - pd.DateOffset(years=years)
        df = df[df.index >= cutoff_date]
        
        if df.empty:
            return {}
            
        # Resample
        if frequency == 'W':
            df = df.resample('W').last().dropna()
        elif frequency == 'M':
            df = df.resample('ME').last().dropna()

        # Calculate statistics
        pe_series = df['pe_ttm'] if 'pe_ttm' in df else pd.Series()
        pb_series = df['pb'] if 'pb' in df else pd.Series()
        
        stats = {
            'pe_ttm': self._calculate_stats(pe_series),
            'pb_ratio': self._calculate_stats(pb_series)
        }
        
        # Chart Data
        MAX_POINTS = 500
        if len(df) > MAX_POINTS:
            step = len(df) // MAX_POINTS
            chart_df = df.iloc[::step]
        else:
            chart_df = df
        
        dates = chart_df.index.strftime('%Y-%m-%d').tolist()
        pe_list = pe_series.reindex(chart_df.index).where(pd.notnull(pe_series), None).tolist() if not pe_series.empty else []
        pb_list = pb_series.reindex(chart_df.index).where(pd.notnull(pb_series), None).tolist() if not pb_series.empty else []
        
        result = {
            'stock_code': stock_code,
            'years': years,
            'frequency': frequency,
            'stats': stats,
            'dates': dates,
            'pe_ttm_list': pe_list,
            'pb_ratio_list': pb_list
        }
        
        if self._enable_cache:
            await self._cache_manager.set(cache_key, result, ttl=86400)
            
        return result

    def _calculate_stats(self, series: pd.Series) -> Dict[str, float]:
        if series.empty:
            return {}
        
        # Remove NaNs and Infs
        s = series.replace([np.inf, -np.inf], np.nan).dropna()
        if s.empty:
            return {}
            
        return {
            'mean': round(float(s.mean()), 2),
            'median': round(float(s.median()), 2),
            'min': round(float(s.min()), 2),
            'max': round(float(s.max()), 2),
            'p25': round(float(np.percentile(s, 25)), 2),
            'p50': round(float(np.percentile(s, 50)), 2),
            'p75': round(float(np.percentile(s, 75)), 2),
            'p90': round(float(np.percentile(s, 90)), 2),
        }
