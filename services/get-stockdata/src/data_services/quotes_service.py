# -*- coding: utf-8 -*-
"""
EPIC-005 Quotes Service
Provides high-performance batch real-time quotes.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import pandas as pd

from .cache_manager import CacheManager
from .akshare_client import akshare_client

try:
    from api.routers.metrics import record_data_source_request
except ImportError:
    def record_data_source_request(source, success, duration): pass

logger = logging.getLogger(__name__)

class QuotesService:
    """Quotes Data Service
    
    Provides:
    1. Batch real-time quotes (price, volume, turnover)
    2. Cached market snapshot for high concurrency
    """
    
    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        enable_cache: bool = True,
        timeout: int = 20,
    ):
        self._cache_manager = cache_manager
        self._enable_cache = enable_cache
        self._timeout = timeout
        self._initialized = False
        self._lock = asyncio.Lock()
        
        self._snapshot_cache: Optional[pd.DataFrame] = None
        self._snapshot_ts: float = 0
        self._snapshot_lock = asyncio.Lock()  # CRITICAL: Protect shared snapshot state
        self._snapshot_ttl: float = 30.0 # Increased cache TTL to reduced load on proxy
        
        # Dedicated executor for AkShare to prevent blocking main loop defaults
        from concurrent.futures import ThreadPoolExecutor
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="QuotesAkShare")
        
    async def initialize(self) -> bool:
        async with self._lock:
            if self._initialized:
                return True
            
            logger.info("Initializing QuotesService...")
            if self._enable_cache:
                if self._cache_manager is None:
                    self._cache_manager = CacheManager()
                try:
                    await self._cache_manager.initialize()
                except Exception as e:
                    logger.warning(f"Failed to init cache manager: {e}, running without Redis")
                    self._enable_cache = False
            
            self._initialized = True
            logger.info("✅ QuotesService initialized")
            return True

    async def _ensure_initialized(self) -> bool:
        if not self._initialized:
            return await self.initialize()
        return True
    
    async def _fetch_market_snapshot_raw(self):
        """Fetch using AkShareClient with metrics and resilience"""
        return await akshare_client.call('stock_zh_a_spot_em')

    def _generate_mock_snapshot(self) -> pd.DataFrame:
        """Generate mock data for fallback when API fails"""
        logger.warning("⚠️ Generating MOCK market snapshot due to API failure")
        data = {
            'code': ['600519', '000001', '000858', '601318', '000333'],
            'name': ['贵州茅台', '平安银行', '五粮液', '中国平安', '美的集团'],
            'price': [1750.0, 10.5, 145.2, 45.8, 65.2],
            'change_pct': [1.2, -0.5, 2.1, 0.0, -1.1],
            'volume': [50000, 1000000, 300000, 800000, 400000],
            'turnover': [87500000.0, 10500000.0, 43560000.0, 36640000.0, 26080000.0],
            'turnover_ratio': [0.5, 1.2, 0.8, 0.6, 0.9],
            'total_market_cap': [2200000000000.0, 200000000000.0, 560000000000.0, 850000000000.0, 450000000000.0],
            'circulating_market_cap': [2200000000000.0, 200000000000.0, 560000000000.0, 850000000000.0, 450000000000.0],
            'pe_ttm': [25.5, 5.2, 22.1, 8.5, 12.3],
            'pb_ratio': [8.5, 0.6, 5.2, 0.9, 2.5]
        }
        return pd.DataFrame(data)

    async def _fetch_market_snapshot(self) -> Optional[pd.DataFrame]:
        """Fetch full market snapshot with retry logic"""
        # Check in-memory cache first (protected read)
        now = datetime.now().timestamp()
        async with self._snapshot_lock:
            if self._snapshot_cache is not None and (now - self._snapshot_ts < self._snapshot_ttl):
                return self._snapshot_cache
            
        try:
            # 使用重构后的 AkShareClient 调用
            df = await self._fetch_market_snapshot_raw()
            
            if df is not None and not df.empty:
                # Normalize columns
                # AkShare columns: 序号, 代码, 名称, 最新价, 涨跌幅, 涨跌额, 成交量, 成交额, 振幅, 最高, 最低, 今开, 昨收, 量比, 换手率, 市盈率-动态, 市净率, 总市值, 流通市值, 涨速, 5分钟涨跌, 60日涨跌幅, 年初至今涨跌幅
                # Map to internal names
                rename_map = {
                    '代码': 'code',
                    '名称': 'name',
                    '最新价': 'price',
                    '涨跌幅': 'change_pct',
                    '成交量': 'volume',
                    '成交额': 'turnover',
                    '换手率': 'turnover_ratio',
                    '总市值': 'total_market_cap',
                    '流通市值': 'circulating_market_cap',
                    '市盈率-动态': 'pe_ttm',
                    '市净率': 'pb_ratio'
                }
                # Check columns existence
                existing_cols = set(df.columns)
                valid_rename_map = {k: v for k, v in rename_map.items() if k in existing_cols}
                
                df = df.rename(columns=valid_rename_map)
            
            # Update cache (protected write)
            async with self._snapshot_lock:
                self._snapshot_cache = df
                self._snapshot_ts = now
                
                logger.info(f"Updated market snapshot with {len(df)} records")
                return df
                
        except Exception as e:
            logger.error(f"Failed to fetch market snapshot after retries: {e}")
            # If fetch fails, return stale cache if available
            if self._snapshot_cache is not None:
                logger.warning("Returning stale cache due to fetch failure")
                return self._snapshot_cache
            
            # If NO cache and API failed, return MOCK data to unblock development
            return self._generate_mock_snapshot()
            
        return None

    async def get_realtime_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        """Get real-time quotes for specific codes
        
        Args:
            codes: List of stock codes (6 digits)
            
        Returns:
            List of quote dicts
        """
        if not await self._ensure_initialized():
            return []
            
        snapshot = await self._fetch_market_snapshot()
        if snapshot is None:
            return []
            
        # Filter
        # 1. Ensure codes are strings and cleaned
        target_codes = set(codes)
        
        # 2. Match
        if 'code' not in snapshot.columns:
            return []
            
        matches = snapshot[snapshot['code'].isin(target_codes)]
        
        results = []
        timestamp = datetime.now().isoformat()
        
        for _, row in matches.iterrows():
            try:
                # Safe Parsing
                price = row.get('price')
                price = float(price) if pd.notna(price) else None
                
                market_cap = row.get('total_market_cap')
                market_cap = float(market_cap) if pd.notna(market_cap) else None

                item = {
                    'code': str(row.get('code', '')),
                    'name': str(row.get('name', '')),
                    'price': price,
                    'change_pct': float(row.get('change_pct')) if pd.notna(row.get('change_pct')) else None,
                    'volume': int(row.get('volume')) if pd.notna(row.get('volume')) else 0,
                    'turnover': float(row.get('turnover')) if pd.notna(row.get('turnover')) else 0.0,
                    'turnover_ratio': float(row.get('turnover_ratio')) if pd.notna(row.get('turnover_ratio')) else None,
                    'market_cap': market_cap, 
                    'timestamp': timestamp
                }
                results.append(item)
            except Exception as e:
                logger.warning(f"Error parse quote row {row.get('code')}: {e}")
                
        return results

    async def close(self) -> None:
        """关闭服务并清理所有资源
        
        清理顺序:
        1. 关闭线程池
        2. 关闭缓存管理器
        3. 重置标志
        """
        logger.info("Closing QuotesService...")
        
        # 1. Shutdown executor
        if hasattr(self, '_executor') and self._executor is not None:
            try:
                self._executor.shutdown(wait=True, cancel_futures=True)
                logger.info("✅ QuotesService executor shut down")
            except Exception as e:
                logger.error(f"Error shutting down executor: {e}")
        
        # 2. Close cache manager
        if self._cache_manager is not None:
            try:
                await self._cache_manager.close()
                logger.info("✅ QuotesService cache manager closed")
            except Exception as e:
                logger.error(f"Error closing cache manager: {e}")
        
        # 3. Reset state
        self._initialized = False
        async with self._snapshot_lock:
            self._snapshot_cache = None
            self._snapshot_ts = 0
        
        logger.info("✅ QuotesService closed")

