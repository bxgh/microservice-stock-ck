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
    ):
        self._cache_manager = cache_manager
        self._enable_cache = enable_cache
        self._timeout = timeout
        
        self._initialized = False
        self._lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
        
        # Use Remote Provider
        self._provider = AkshareProvider()
        
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
        """Get real-time valuation metrics via Remote API (Robust)"""
        if not await self._ensure_initialized():
            raise RuntimeError("ValuationService not initialized")

        cache_key = f"valuation:current:{stock_code}"
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            async with self._stats_lock:
                self._stats['cache_misses'] += 1

        # 1. Fetch Meta for Market Cap (via STOCK_INFO)
        # 2. Fetch Latest TTM PE/PB/PS from Baidu (more reliable than Spot)
        
        async def fetch_meta():
            res = await self._provider.fetch(DataType.META, symbol=stock_code)
            if res.success and not res.data.empty:
                return res.data.iloc[0].to_dict()
            return {}

        async def fetch_baidu_latest(indicator):
            res = await self._provider.fetch(DataType.VALUATION_BAIDU, symbol=stock_code, indicator=indicator)
            if res.success and not res.data.empty:
                # Baidu returns history, sorted by date asc by default? Let's sort to be safe
                df = res.data
                if 'date' in df.columns:
                    df = df.sort_values('date')
                elif '日期' in df.columns:
                     df = df.sort_values('日期')
                return df.iloc[-1]['value']
            return None

        # Execute concurrently
        info_dict, pe_ttm, pb_ratio, ps_ratio = await asyncio.gather(
            fetch_meta(),
            fetch_baidu_latest("市盈率(TTM)"),
            fetch_baidu_latest("市净率"),
            fetch_baidu_latest("市销率(TTM)")
        )

        def safe_float(val):
            try:
                return float(val) if val is not None else None
            except:
                return None

        # Convert to billion yuan
        def to_billion(val):
            f = safe_float(val)
            return round(f / 100000000, 4) if f is not None else None
            
        result = {
            'stock_code': stock_code,
            'report_date': datetime.now().strftime('%Y%m%d'),
            'total_market_cap': to_billion(info_dict.get('总市值')),
            'circulating_market_cap': to_billion(info_dict.get('流通市值')),
            'pe_ttm': safe_float(pe_ttm),
            'pe_static': None, # skipped
            'pb_ratio': safe_float(pb_ratio),
            'ps_ratio': safe_float(ps_ratio), 
            'pcf_ratio': None,
            'dividend_yield_ttm': None 
        }
        
        if self._enable_cache:
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
