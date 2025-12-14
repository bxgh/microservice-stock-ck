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
                
        # Optimization: Fetch spot data and performance data in PARALLEL
        spot_table_key = "valuation:spot_table_full"
        perf_table_key = "financial:performance_report:latest"
        
        # Define tasks for fetching with error handling
        async def fetch_spot():
            df = None
            try:
                if self._enable_cache:
                    df = await self._cache_manager.get(spot_table_key)
                if df is None:
                    try:
                        df = await akshare_client.call('stock_zh_a_spot_em')
                        if df is not None and self._enable_cache:
                            await self._cache_manager.set(spot_table_key, df, ttl=120)
                    except Exception as e:
                        logger.error(f"Failed to fetch stock_zh_a_spot_em: {e}")
                        # If spot data fails, we can't do much. Return None.
            except Exception as e:
                logger.error(f"Error in fetch_spot: {e}")
            return df

        async def fetch_perf():
            df = None
            try:
                if self._enable_cache:
                    df = await self._cache_manager.get(perf_table_key)
                if df is None:
                     # Determine date logic
                    curr_month = datetime.now().month
                    curr_year = datetime.now().year
                    if curr_month < 4: report_date = f"{curr_year-1}0930"
                    elif curr_month < 8: report_date = f"{curr_year}0331"
                    elif curr_month < 10: report_date = f"{curr_year}0630"
                    else: report_date = f"{curr_year}0930"
                    
                    try:
                        df = await akshare_client.call('stock_yjbb_em', date=report_date)
                        if df is not None and not df.empty and self._enable_cache:
                            await self._cache_manager.set(perf_table_key, df, ttl=86400)
                    except Exception as e:
                         logger.error(f"Failed to fetch stock_yjbb_em: {e}")
            except Exception as e:
                logger.error(f"Error in fetch_perf: {e}")
            return df


        # Execute in parallel
        # Note: exceptions inside coroutines are now caught, so gather won't crash
        full_df, perf_df = await asyncio.gather(fetch_spot(), fetch_perf())

        # Check if spot data is valid
        is_spot_valid = full_df is not None and not full_df.empty
        
        # --- Fallback Logic: Baostock ---
        from .baostock_client import baostock_client
        use_baostock = False
        
        if not is_spot_valid:
            logger.warning(f"AkShare spot data unavailable for industry: {industry_name}. Attempting Fallback to Baostock...")
            ind_df = await self._fetch_from_baostock(industry_name)
            if not ind_df.empty:
                use_baostock = True
                logger.info(f"✅ Fallback to Baostock successful. Retrieved {len(ind_df)} stocks.")
            else:
                 logger.error(f"❌ Fallback to Baostock failed or empty.")
                 return {}
        else:
            # AkShare Logic (Existing)
            # Check if we have industry column
            has_industry_col = False
            for col in ['行业', '所属行业', '板块']:
                if col in full_df.columns:
                    industry_col = col
                    has_industry_col = True
                    break
            
            ind_df = pd.DataFrame()
            if has_industry_col:
                ind_df = full_df[full_df[industry_col] == industry_name]
            else:
                try:
                    cons_df = await akshare_client.call('stock_board_industry_cons_em', symbol=industry_name)
                    if cons_df is not None and not cons_df.empty:
                        codes = set(cons_df['代码'].tolist())
                        ind_df = full_df[full_df['代码'].isin(codes)]
                except Exception as e:
                     logger.error(f"Failed to fetch industry constituents for {industry_name}: {e}")

        if ind_df.empty:
            return {}
            
        # 3. Calculate Stats for PE(TTM), PB
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

        if use_baostock:
            # Baostock DF columns: [code, peTTM, pbMRQ, ...]
            pe_stats = calc_stats(ind_df['peTTM']) if 'peTTM' in ind_df.columns else {}
            pb_stats = calc_stats(ind_df['pbMRQ']) if 'pbMRQ' in ind_df.columns else {}
            # Baostock currently doesn't provide ROE/Growth seamlessly in the same call without loops
            # So we might skip ROE/Growth for fallback, or implement loop (slow)
            # For MVP fallback, let's keep ROE/Growth empty or try to fetch if perf_df (AkShare) happened to work?
            # Usually if spot failed due to proxy, perf might fail too. 
            # But let's check perf_df from above
            roe_stats = {}
            revenue_growth_stats = {}
            # If we have perf_df from AkShare (maybe different API worked?), we can map it
            # But likely it failed too.
            
        else:
            # AkShare Logic
            pe_col = '市盈率-动态' if '市盈率-动态' in ind_df.columns else '市盈率'
            pb_col = '市净率'
            
            pe_stats = calc_stats(ind_df[pe_col]) if pe_col in ind_df.columns else {}
            pb_stats = calc_stats(ind_df[pb_col]) if pb_col in ind_df.columns else {}
            
            # 4. Calculate ROE & Growth Stats (From parallel fetched perf_df)
            roe_stats = {}
            revenue_growth_stats = {}
            
            if perf_df is not None and not perf_df.empty:
                # Filter by codes in industry
                company_codes = set(ind_df['代码'].tolist())
                if '股票代码' in perf_df.columns:
                     ind_perf_df = perf_df[perf_df['股票代码'].isin(company_codes)]
                
                     if not ind_perf_df.empty:
                        # Calculate ROE Stats
                        if '净资产收益率' in ind_perf_df.columns:
                            roe_stats = calc_stats(ind_perf_df['净资产收益率'])
                        # Calculate Growth Stats
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

    async def _fetch_from_baostock(self, industry_name: str) -> pd.DataFrame:
        """Fetch industry data from Baostock (Fallback)"""
        from .baostock_client import baostock_client
        
        # 1. Get All Industry Data
        # Baostock doesn't support filtering by industry name directly in query
        # We must fetch all and filter in memory
        
        industry_cache_key = "baostock:industry_list"
        df_ind = None
        
        if self._enable_cache:
            df_ind = await self._cache_manager.get(industry_cache_key)
            
        if df_ind is None:
             # Run sync in executor
             loop = asyncio.get_event_loop()
             df_ind = await loop.run_in_executor(None, lambda: baostock_client.query_stock_industry())
             if df_ind is not None and not df_ind.empty and self._enable_cache:
                 await self._cache_manager.set(industry_cache_key, df_ind, ttl=86400*7)
        
        if df_ind is None or df_ind.empty:
            return pd.DataFrame()
            
        # Filter by name
        # Columns: [code, code_name, industry, industryClassification]
        # Match 'industry' column
        target_df = df_ind[df_ind['industry'] == industry_name]
        
        if target_df.empty:
            return pd.DataFrame()
            
        stocks = target_df['code'].tolist()
        if not stocks:
            return pd.DataFrame()
            
        # 2. Fetch Valuation Data for these stocks
        # Baostock query_history_k_data_plus gets PE/PB
        # Doing this for 50+ stocks sequentially is SLOW.
        # But Baostock doesn't support batch query for standard K data easily?
        # Ideally we parallelize this.
        
        # Limit to top 30 stocks to avoid timeout for fallback? 
        # Or use a thread pool for 50 stocks.
        
        stocks_to_fetch = stocks[:50] # Limit for performance fallback
        
        async def fetch_one(code):
             loop = asyncio.get_event_loop()
             # Get latest 1 day
             df = await loop.run_in_executor(None, lambda: baostock_client.query_history_k_data_plus(
                 code, "peTTM,pbMRQ"
             ))
             if df is not None and not df.empty:
                 return df.iloc[-1] # Latest row
             return None

        # NOTE: Attempted P1 optimization with Semaphore(5) limited concurrency
        # but caused network errors ("Invalid Distance", decompression failures)
        # Reverting to sequential for stability. Tradeoff: 2.5s latency acceptable
        # for fallback scenario (rare, only when AkShare fails).
        results = []
        for code in stocks_to_fetch:
            res = await fetch_one(code)
            results.append(res)
            await asyncio.sleep(0.05)  # Prevent connection overload
        
        valid_data = [r for r in results if r is not None]
        if not valid_data:
            return pd.DataFrame()
            
        result_df = pd.DataFrame(valid_data)
        return result_df

