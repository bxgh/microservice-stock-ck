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
        timeout: int = 45, # Higher timeout for heavy valuation queries
    ):
        self._cache_manager = cache_manager
        self._enable_cache = enable_cache
        self._timeout = timeout
        
        self._initialized = False
        self._lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
        
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
            
            self._initialized = True
            logger.info("✅ ValuationService initialized")
            return True

    async def close(self) -> None:
        if self._cache_manager:
            await self._cache_manager.close()
        self._initialized = False
        logger.info("ValuationService closed")

    async def _ensure_initialized(self) -> bool:
        if not self._initialized:
            return await self.initialize()
        return True

    async def _call_akshare(self, func_name: str, **kwargs) -> Optional[pd.DataFrame]:
        """Call akshare via shared client"""
        from .akshare_client import akshare_client
        return await akshare_client.call(func_name, **kwargs)

    async def get_current_valuation(self, stock_code: str) -> Dict[str, Any]:
        """Get real-time valuation metrics"""
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

        # Use stock_individual_info_em for fast single-stock info
        info_df = await self._call_akshare('stock_individual_info_em', symbol=stock_code)
        
        if info_df is None or info_df.empty:
            return {}
            
        # Parse info_df (columns: item, value)
        info_dict = dict(zip(info_df['item'], info_df['value']))
        
        # To get PE/PB TTM, we check stock_zh_valuation_baidu for specific indicators
        # Since spot_em is flaky, we use baidu for TTM ratios which is more reliable
        # We fetch "总市值", "市盈率(TTM)", "市净率", "市销率(TTM)" concurrently-ish or just one by one
        # Note: Baidu API returns history, we take the last row
        
        async def fetch_baidu_latest(indicator):
             df = await self._call_akshare('stock_zh_valuation_baidu', symbol=stock_code, indicator=indicator)
             if df is not None and not df.empty:
                 return df.iloc[-1]['value']
             return None

        pe_ttm, pb_ratio, ps_ratio = await asyncio.gather(
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

        # Info Dict usage for backup or specific fields
        # info_dict has '总市值', '流通市值'
        
        result = {
            'stock_code': stock_code,
            'report_date': datetime.now().strftime('%Y%m%d'),
            
            'total_market_cap': to_billion(info_dict.get('总市值')),
            'circulating_market_cap': to_billion(info_dict.get('流通市值')),
            
            'pe_ttm': safe_float(pe_ttm),
            'pe_static': safe_float(info_dict.get('市盈率(动)')), # Fallback to dynamic if needed
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
        """Get historical valuation with statistics via Baidu API"""
        if not await self._ensure_initialized():
             raise RuntimeError("ValuationService not initialized")

        cache_key = f"valuation:history:{stock_code}:{years}:{frequency}"
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached:
                return cached

        # Use stock_zh_valuation_baidu for history
        # Need to fetch PE and PB separately and merge
        
        async def fetch_series(indicator, col_name):
            df = await self._call_akshare('stock_zh_valuation_baidu', symbol=stock_code, indicator=indicator)
            if df is not None:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                df = df.rename(columns={'value': col_name})
                return df
            return pd.DataFrame()

        pe_df, pb_df = await asyncio.gather(
            fetch_series("市盈率(TTM)", "pe_ttm"),
            fetch_series("市净率", "pb")
        )
        
        # Merge
        if pe_df.empty and pb_df.empty:
            return {}
            
        merged = pe_df.join(pb_df, how='outer').sort_index()
        
        # Filter last N years
        cutoff_date = pd.Timestamp.now() - pd.DateOffset(years=years)
        merged = merged[merged.index >= cutoff_date]
        
        if merged.empty:
            return {}
            
        # Resample if needed (merged is Date indexed)
        # Assuming frequency 'D', 'W', 'M'
        if frequency == 'W':
            merged = merged.resample('W').last().dropna()
        elif frequency == 'M':
            merged = merged.resample('ME').last().dropna()

        # Calculate statistics
        stats = {
            'pe_ttm': self._calculate_stats(merged['pe_ttm'] if 'pe_ttm' in merged else pd.Series()),
            'pb_ratio': self._calculate_stats(merged['pb'] if 'pb' in merged else pd.Series())
        }
        
        # Chart Data
        MAX_POINTS = 500
        if len(merged) > MAX_POINTS:
            step = len(merged) // MAX_POINTS
            chart_df = merged.iloc[::step]
        else:
            chart_df = merged
        
        dates = chart_df.index.strftime('%Y-%m-%d').tolist()
        pe_list = chart_df['pe_ttm'].where(pd.notnull(chart_df['pe_ttm']), None).tolist() if 'pe_ttm' in chart_df else []
        pb_list = chart_df['pb'].where(pd.notnull(chart_df['pb']), None).tolist() if 'pb' in chart_df else []
        
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
