# -*- coding: utf-8 -*-
"""
EPIC-007 财务报表服务 (FinancialService)

提供个股财务指标和财务报表摘要查询。

核心功能:
1. 财务摘要: 利润表/资产负债表/现金流量表关键指标
2. 财务指标: PE/PB/ROE/EPS等分析指标
3. PE/PB快速查询

数据源: akshare

@author: EPIC-007 Story 007.08
@date: 2025-12-07
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import pandas as pd

from .cache_manager import CacheManager
from .time_aware_strategy import get_time_strategy

logger = logging.getLogger(__name__)


class FinancialService:
    """财务报表服务
    
    提供个股财务指标和财务报表摘要查询。
    
    Example:
        service = FinancialService()
        await service.initialize()
        
        # 财务摘要
        summary = await service.get_financial_summary('600519')
        
        # 财务指标
        indicators = await service.get_financial_indicators('600519')
        
        # PE/PB
        pe_pb = await service.get_pe_pb('600519')
        
        await service.close()
    """
    
    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        enable_cache: bool = True,
        timeout: int = 30,
    ):
        """初始化
        
        Args:
            cache_manager: 缓存管理器
            enable_cache: 是否启用缓存
            timeout: API 超时时间(秒)
        """
        self._cache_manager = cache_manager
        self._enable_cache = enable_cache
        self._timeout = timeout
        
        self._initialized = False
        self._lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
        
        # 统计信息
        self._stats: Dict[str, Any] = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'akshare_calls': 0,
            'timeout_errors': 0,
        }
    
    async def initialize(self) -> bool:
        """初始化服务"""
        async with self._lock:
            if self._initialized:
                return True
            
            logger.info("Initializing FinancialService...")
            
            # 初始化缓存管理器
            if self._enable_cache:
                if self._cache_manager is None:
                    self._cache_manager = CacheManager()
                
                if not await self._cache_manager.initialize():
                    logger.warning("CacheManager init failed, caching disabled")
                    self._enable_cache = False
            
            self._initialized = True
            logger.info("✅ FinancialService initialized")
            return True
    
    async def close(self) -> None:
        """关闭服务"""
        if self._cache_manager:
            await self._cache_manager.close()
        
        self._initialized = False
        logger.info("FinancialService closed")
    
    async def _ensure_initialized(self) -> bool:
        """确保服务已初始化"""
        if not self._initialized:
            return await self.initialize()
        return True
    
    async def _call_akshare(self, func_name: str, **kwargs) -> Optional[pd.DataFrame]:
        """调用 akshare API
        
        Args:
            func_name: akshare 函数名
            **kwargs: 函数参数
            
        Returns:
            DataFrame or None
        """
        try:
            import akshare as ak
            
            async with self._stats_lock:
                self._stats['akshare_calls'] += 1
            
            func = getattr(ak, func_name)
            loop = asyncio.get_event_loop()
            
            # 使用超时控制
            df = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: func(**kwargs)),
                timeout=self._timeout
            )
            
            return df if df is not None and not df.empty else None
            
        except asyncio.TimeoutError:
            logger.error(f"akshare {func_name} timeout ({self._timeout}s)")
            async with self._stats_lock:
                self._stats['timeout_errors'] += 1
            return None
        except Exception as e:
            logger.error(f"akshare {func_name} failed: {e}")
            return None
    
    # ========== 财务摘要 ==========
    
    async def get_financial_summary(
        self,
        code: str,
    ) -> Dict[str, Any]:
        """获取财务摘要
        
        Args:
            code: 股票代码 (如 '600519')
            
        Returns:
            Dict: 财务摘要信息
        """
        if not await self._ensure_initialized():
            raise RuntimeError("FinancialService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 缓存键
        cache_key = f"financial:summary:{code}"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        # 调用 akshare
        df = await self._call_akshare('stock_financial_abstract', symbol=code)
        
        if df is None or df.empty:
            return {}
        
        # 转换为字典格式
        result = self._parse_financial_summary(df)
        
        # 缓存 (1天，财务数据更新频率低)
        if self._enable_cache and result:
            await self._cache_manager.set(cache_key, result, ttl=86400)
        
        return result
    
    def _parse_financial_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """解析财务摘要数据"""
        try:
            result = {
                'code': '',
                'report_date': '',
                'data': {},
            }
            
            # 获取最近的报告期
            date_cols = [col for col in df.columns if col not in ['选项', '指标']]
            if date_cols:
                latest_date = date_cols[0]
                result['report_date'] = latest_date
                
                # 提取关键指标
                for _, row in df.iterrows():
                    indicator = row.get('指标', row.get('选项', ''))
                    value = row.get(latest_date, None)
                    if indicator and pd.notna(value):
                        result['data'][indicator] = value
            
            return result
            
        except Exception as e:
            logger.error(f"Parse financial summary failed: {e}")
            return {}
    
    # ========== 财务指标 ==========
    
    async def get_financial_indicators(
        self,
        code: str,
        start_year: str = '2020',
    ) -> pd.DataFrame:
        """获取财务分析指标
        
        Args:
            code: 股票代码
            start_year: 起始年份
            
        Returns:
            DataFrame: 财务指标数据
        """
        if not await self._ensure_initialized():
            raise RuntimeError("FinancialService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 缓存键
        cache_key = f"financial:indicators:{code}:{start_year}"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        # 调用 akshare
        df = await self._call_akshare(
            'stock_financial_analysis_indicator',
            symbol=code,
            start_year=start_year
        )
        
        if df is None:
            return pd.DataFrame()
        
        # 缓存 (1天)
        if self._enable_cache and not df.empty:
            await self._cache_manager.set(cache_key, df, ttl=86400)
        
        return df
    
    # ========== PE/PB 快速查询 ==========
    
    async def get_pe_pb(
        self,
        code: str,
    ) -> Dict[str, Any]:
        """获取 PE/PB 估值指标
        
        Args:
            code: 股票代码
            
        Returns:
            Dict: {'pe': float, 'pb': float, 'pe_ttm': float}
        """
        if not await self._ensure_initialized():
            raise RuntimeError("FinancialService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 缓存键
        cache_key = f"financial:pe_pb:{code}"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        result = {
            'pe': None,
            'pb': None,
            'pe_ttm': None,
            'code': code,
        }
        
        # 从财务摘要中提取
        summary = await self.get_financial_summary(code)
        
        if summary and 'data' in summary:
            data = summary['data']
            # 尝试提取 PE/PB 相关指标
            for key, value in data.items():
                key_lower = key.lower()
                if 'pe' in key_lower or '市盈率' in key:
                    try:
                        result['pe'] = float(value)
                    except (ValueError, TypeError):
                        pass
                elif 'pb' in key_lower or '市净率' in key:
                    try:
                        result['pb'] = float(value)
                    except (ValueError, TypeError):
                        pass
        
        # 缓存 (时段感知 TTL)
        if self._enable_cache:
            strategy = get_time_strategy()
            ttl = strategy.get_cache_ttl('ranking')  # 使用 ranking 的 TTL
            await self._cache_manager.set(cache_key, result, ttl=ttl)
        
        return result
    
    # ========== 监控统计 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        
        if stats['total_requests'] > 0:
            stats['cache_hit_rate'] = f"{stats['cache_hits'] / stats['total_requests'] * 100:.1f}%"
        else:
            stats['cache_hit_rate'] = "N/A"
        
        return stats
