# -*- coding: utf-8 -*-
"""
EPIC-002 Industry Service
Provides industry-level statistics and comparison data.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from .cache_manager import CacheManager
from .akshare_client import akshare_client

logger = logging.getLogger(__name__)

class IndustryService:
    """Industry Data Service
    
    Provides:
    1. Industry classification for stocks
    2. Industry constituents
    3. Industry-level valuation statistics (PE/PB/ROE distribution)
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
        
    async def initialize(self) -> bool:
        async with self._lock:
            if self._initialized:
                return True
            
            logger.info("Initializing IndustryService...")
            if self._enable_cache:
                if self._cache_manager is None:
                    self._cache_manager = CacheManager()
                if not await self._cache_manager.initialize():
                    self._enable_cache = False
            
            self._initialized = True
            logger.info("✅ IndustryService initialized")
            return True

    async def _ensure_initialized(self) -> bool:
        if not self._initialized:
            return await self.initialize()
        return True

    async def get_industry_info(self, stock_code: str) -> Dict[str, str]:
        """Get industry classification for a stock
        
        Returns:
            Dict: {'industry': '行业名称', 'sector': '板块名称'}
        """
        if not await self._ensure_initialized():
             return {}

        cache_key = f"industry:info:{stock_code}"
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached:
                return cached
        
        # Use stock_individual_info_em
        df = await akshare_client.call('stock_individual_info_em', symbol=stock_code)
        
        result = {'industry': '', 'sector': '', 'listing_date': None}
        if df is not None and not df.empty:
            info_dict = dict(zip(df['item'], df['value']))
            result['industry'] = info_dict.get('行业', '')
            
            # Parse listing date (YYYYMMDD)
            l_date = str(info_dict.get('上市时间', ''))
            if l_date and len(l_date) == 8:
                try:
                    dt = datetime.strptime(l_date, '%Y%m%d')
                    result['listing_date'] = dt
                except ValueError:
                    pass
            # Try to infer sector or get it from elsewhere? 
            # Currently '行业' is usually the SW level 2 or similar
        
        if self._enable_cache and result['industry']:
            await self._cache_manager.set(cache_key, result, ttl=86400 * 3) # Cache for 3 days
            
        return result

    async def get_industry_stats(self, industry_name: str) -> Dict[str, Any]:
        """Get statistics for an industry
        
        Args:
            industry_name: 行业名称 (e.g. '酿酒行业')
        """
        if not await self._ensure_initialized():
            raise RuntimeError("IndustryService not initialized")
            
        cache_key = f"industry:stats:{industry_name}"
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached:
                return cached
                
        # 1. Get all spot data (cached heavily)
        # We use a shared key for spot table to avoid spamming
        table_cache_key = "valuation:spot_table_full" 
        full_df = None
        if self._enable_cache:
            full_df = await self._cache_manager.get(table_cache_key)
            
        if full_df is None:
            full_df = await akshare_client.call('stock_zh_a_spot_em')
            if full_df is not None and self._enable_cache:
                 await self._cache_manager.set(table_cache_key, full_df, ttl=120)

        if full_df is None or full_df.empty:
            return {}

        # 2. Filter by industry
        # stock_zh_a_spot_em usually has '名称', '代码', '市盈率-动态' etc. but MAYBE NOT '行业'
        # If '行业' is not in spot data, we cannot filter easily without fetching cons list.
        # Let's assume we need to fetch constituents first if industry col is missing.
        
        # Check if we have industry column
        has_industry_col = False
        for col in ['行业', '所属行业', '板块']:
            if col in full_df.columns:
                industry_col = col
                has_industry_col = True
                break
        
        target_stocks = []
        if has_industry_col:
            # Filter in memory
            ind_df = full_df[full_df[industry_col] == industry_name]
        else:
            # Must fetch constituents list
            # stock_board_industry_cons_em
            cons_df = await akshare_client.call('stock_board_industry_cons_em', symbol=industry_name)
            if cons_df is None or cons_df.empty:
                return {} # Can't find industry or stocks
                
            codes = set(cons_df['代码'].tolist())
            ind_df = full_df[full_df['代码'].isin(codes)]
            
        if ind_df.empty:
            return {}
            
        # 3. Calculate Stats for PE(TTM), PB
        # Spot EM fields: '市盈率-动态', '市净率'
        # Note: '市盈率-动态' is usually PE(TTM) or close to it in EM spot
        

        def calc_stats(series):
            # Clean data
            s = pd.to_numeric(series, errors='coerce').dropna()
            # Filter reasonable range for stats
            # PE/PB > 0, others can be negative but let's filter extreme outliers
            s = s[(s > -1000) & (s < 10000)]
            if s.empty: return {}
            return {
                'mean': round(float(s.mean()), 2),
                'median': round(float(s.median()), 2),
                'p25': round(float(np.percentile(s, 25)), 2),
                'p50': round(float(np.percentile(s, 50)), 2),
                'p75': round(float(np.percentile(s, 75)), 2),
                'min': round(float(s.min()), 2),
                'max': round(float(s.max()), 2),
                'count': int(len(s))
            }

        pe_col = '市盈率-动态' if '市盈率-动态' in ind_df.columns else '市盈率'
        pb_col = '市净率'
        
        pe_stats = calc_stats(ind_df[pe_col]) if pe_col in ind_df.columns else {}
        pb_stats = calc_stats(ind_df[pb_col]) if pb_col in ind_df.columns else {}
        
        # 4. Calculate ROE & Growth Stats (Batch Fetch)
        roe_stats = {}
        revenue_growth_stats = {}
        
        # Determine latest report date (approximate)
        # Strategy: Try cache first, if missing fetch fresh
        perf_cache_key = "financial:performance_report:latest"
        perf_df = None
        
        if self._enable_cache:
            perf_df = await self._cache_manager.get(perf_cache_key)
            
        if perf_df is None:
            # Determine date: try to fetch from a recent period
            # For simplicity, we can fetch without date to get "latest" or use specific logic
            # ak.stock_yjbb_em() fetches latest available if date not specified? Not sure.
            # Let's try explicit date logic similar to script
            curr_month = datetime.now().month
            curr_year = datetime.now().year
            if curr_month < 4: report_date = f"{curr_year-1}0930"
            elif curr_month < 8: report_date = f"{curr_year}0331"
            elif curr_month < 10: report_date = f"{curr_year}0630"
            else: report_date = f"{curr_year}0930"
            
            perf_df = await akshare_client.call('stock_yjbb_em', date=report_date)
            
            if perf_df is not None and not perf_df.empty:
                 if self._enable_cache:
                    # Cache for 1 day as this data changes slowly
                    await self._cache_manager.set(perf_cache_key, perf_df, ttl=86400)
        
        if perf_df is not None and not perf_df.empty:
            # Filter by codes in industry
            company_codes = set(ind_df['代码'].tolist())
            ind_perf_df = perf_df[perf_df['股票代码'].isin(company_codes)]
            
            if not ind_perf_df.empty:
                # Calculate ROE Stats
                # Column: 净资产收益率
                if '净资产收益率' in ind_perf_df.columns:
                    roe_stats = calc_stats(ind_perf_df['净资产收益率'])
                    
                # Calculate Growth Stats
                # Column: 营业总收入-同比增长
                if '营业总收入-同比增长' in ind_perf_df.columns:
                    revenue_growth_stats = calc_stats(ind_perf_df['营业总收入-同比增长'])

        result = {
            'industry_code': '', 
            'industry_name': industry_name,
            'stock_count': len(ind_df),
            'report_date': datetime.now().strftime('%Y%m%d'),
            'pe_ttm_stats': pe_stats,
            'pb_ratio_stats': pb_stats,
            'roe_stats': roe_stats,
            'revenue_growth_stats': revenue_growth_stats
        }
        
        if self._enable_cache:
            await self._cache_manager.set(cache_key, result, ttl=86400)
            
        return result
