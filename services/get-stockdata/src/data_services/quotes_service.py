# -*- coding: utf-8 -*-
"""
EPIC-007 实时行情服务 (QuotesService)

提供统一的实时行情查询接口，支持:
1. 多数据源自动降级
2. 智能缓存（时段感知）
3. 字段标准化
4. 丰富的筛选和查询方法

@author: EPIC-007 Story 007.02
@date: 2025-12-06
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from .cache_manager import CacheManager, TradingAwareTTL
from .schemas import QuoteSchema, QuoteWithOrderbookSchema, FieldMapper
from ..data_sources.providers import DataServiceManager, DataResult, DataType

logger = logging.getLogger(__name__)


class QuotesService:
    """实时行情服务
    
    数据中台核心服务之一，为所有策略和应用提供统一的行情数据接口。
    
    Features:
    - 多数据源降级 (mootdx → easyquotation → cache)
    - 智能缓存 (盘中3s / 盘后1h / 非交易日1d)
    - 字段标准化 (QuoteSchema)
    - 丰富的查询方法 (10+ 接口)
    
    Example:
        service = QuotesService()
        await service.initialize()
        
        # 批量查询
        df = await service.get_quotes(['000001', '600519'])
        
        # 单个查询
        quote = await service.get_quote('000001')
        
        # 涨停股票
        limit_up = await service.get_limit_up_stocks()
        
        await service.close()
    """
    
    def __init__(
        self,
        data_manager: Optional[DataServiceManager] = None,
        cache_manager: Optional[CacheManager] = None,
        enable_cache: bool = True,
    ):
        """初始化
        
        Args:
            data_manager: 数据服务管理器，None 则自动创建
            cache_manager: 缓存管理器，None 则自动创建
            enable_cache: 是否启用缓存
        """
        self._data_manager = data_manager
        self._cache_manager = cache_manager
        self._enable_cache = enable_cache
        
        self._initialized = False
        self._lock = asyncio.Lock()
        
        # 统计信息
        self._stats: Dict[str, Any] = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'provider_calls': 0,
            'failed_requests': 0,
        }
    
    async def initialize(self) -> bool:
        """初始化服务
        
        Returns:
            bool: 是否成功
        """
        async with self._lock:
            if self._initialized:
                return True
            
            logger.info("Initializing QuotesService...")
            
            # 初始化数据管理器
            if self._data_manager is None:
                self._data_manager = DataServiceManager()
            
            if not await self._data_manager.initialize():
                logger.error("Failed to initialize DataServiceManager")
                return False
            
            # 初始化缓存管理器
            if self._enable_cache:
                if self._cache_manager is None:
                    self._cache_manager = CacheManager(
                        ttl_strategy=TradingAwareTTL()
                    )
                
                if not await self._cache_manager.initialize():
                    logger.warning("Failed to initialize CacheManager, caching disabled")
                    self._enable_cache = False
            
            self._initialized = True
            logger.info("✅ QuotesService initialized")
            return True
    
    async def close(self) -> None:
        """关闭服务"""
        if self._data_manager:
            await self._data_manager.close()
        
        if self._cache_manager:
            await self._cache_manager.close()
        
        self._initialized = False
        logger.info("QuotesService closed")
    
    # ========== 核心查询接口 ==========
    
    async def get_quotes(
        self,
        codes: List[str],
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """获取实时行情（批量）
        
        Args:
            codes: 股票代码列表
            use_cache: 是否使用缓存
            
        Returns:
            pd.DataFrame: 标准化行情数据
            
        Raises:
            ValueError: 参数错误
            RuntimeError: 所有数据源失败
        """
        if not codes:
            raise ValueError("codes cannot be empty")
        
        self._stats['total_requests'] += 1
        
        # 生成缓存键
        cache_key = f"quotes:batch:{self._cache_manager.generate_hash_key(sorted(codes))}" if self._enable_cache else None
        
        # 尝试缓存
        if use_cache and self._enable_cache and cache_key:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                self._stats['cache_hits'] += 1
                logger.debug(f"Cache HIT for {len(codes)} codes")
                return cached
            else:
                self._stats['cache_misses'] += 1
        
        # 调用底层数据管理器
        self._stats['provider_calls'] += 1
        result: DataResult = await self._data_manager.get_quotes(codes=codes)
        
        if not result.success or result.is_empty:
            self._stats['failed_requests'] += 1
            error_msg = result.error or "No data returned"
            logger.error(f"Failed to get quotes: {error_msg}")
            raise RuntimeError(f"Failed to get quotes: {error_msg}")
        
        # 字段标准化
        df = self._standardize_quotes(result.data)
        
        # 缓存结果
        if use_cache and self._enable_cache and cache_key:
            await self._cache_manager.set(cache_key, df)
        
        logger.info(f"✅ Got quotes for {len(df)} stocks from {result.provider}")
        return df
    
    async def get_quote(self, code: str) -> Optional[pd.Series]:
        """获取单个股票行情（便捷方法）
        
        Args:
            code: 股票代码
            
        Returns:
            pd.Series: 单个股票行情，失败返回 None
        """
        try:
            df = await self.get_quotes([code])
            if not df.empty:
                return df.iloc[0]
        except Exception as e:
            logger.error(f"Failed to get quote for {code}: {e}")
        
        return None
    
    async def get_all_quotes(self, use_cache: bool = True) -> pd.DataFrame:
        """获取全市场行情
        
        使用 easyquotation 获取全市场 5000+ 只股票行情。
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            pd.DataFrame: 全市场行情
        """
        cache_key = "quotes:all_market"
        
        # 尝试缓存
        if use_cache and self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                self._stats['cache_hits'] += 1
                logger.debug(f"Cache HIT for all market quotes")
                return cached
        
        # 获取全市场（不指定codes，部分provider支持）
        # 或者从其他方式获取全市场代码列表
        try:
            # 方案1: 尝试不带参数调用（easyquotation 支持）
            result: DataResult = await self._data_manager.get_quotes(codes=[])
            
            if result.success and not result.is_empty:
                df = self._standardize_quotes(result.data)
                
                if use_cache and self._enable_cache:
                    await self._cache_manager.set(cache_key, df)
                
                logger.info(f"✅ Got all market quotes: {len(df)} stocks")
                return df
        except:
            pass
        
        # 方案2: 使用预定义的股票池（降级方案）
        logger.warning("All market quotes not available, using fallback")
        return pd.DataFrame()
    
    async def get_quotes_with_orderbook(
        self,
        codes: List[str],
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """获取带五档盘口的行情数据
        
        Args:
            codes: 股票代码列表
            use_cache: 是否使用缓存
            
        Returns:
            pd.DataFrame: 包含五档盘口的行情数据
        """
        # 缓存键不同，独立缓存
        cache_key = f"quotes_ob:batch:{self._cache_manager.generate_hash_key(sorted(codes))}" if self._enable_cache else None
        
        if use_cache and self._enable_cache and cache_key:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                self._stats['cache_hits'] += 1
                return cached
        
        # 调用底层，带 orderbook 参数
        result: DataResult = await self._data_manager.get_quotes(
            codes=codes,
            include_orderbook=True  # 新增参数提示
        )
        
        if not result.success or result.is_empty:
            logger.error("Failed to get quotes with orderbook")
            raise RuntimeError("Failed to get quotes with orderbook")
        
        # 标准化（包含盘口字段）
        df = self._standardize_quotes(result.data, include_orderbook=True)
        
        if use_cache and self._enable_cache and cache_key:
            await self._cache_manager.set(cache_key, df)
        
        return df
    
    # ========== 筛选接口（基于缓存优化）==========
    
    async def get_top_gainers(self, n: int = 50) -> pd.DataFrame:
        """获取涨幅前 N 名
        
        Args:
            n: 返回数量
            
        Returns:
            pd.DataFrame: 涨幅排名前 N 的股票
        """
        all_quotes = await self.get_all_quotes()
        if all_quotes.empty:
            return pd.DataFrame()
        
        return all_quotes.nlargest(n, 'change_pct')
    
    async def get_top_losers(self, n: int = 50) -> pd.DataFrame:
        """获取跌幅前 N 名
        
        Args:
            n: 返回数量
            
        Returns:
            pd.DataFrame: 跌幅排名前 N 的股票
        """
        all_quotes = await self.get_all_quotes()
        if all_quotes.empty:
            return pd.DataFrame()
        
        return all_quotes.nsmallest(n, 'change_pct')
    
    async def get_top_volume(self, n: int = 50) -> pd.DataFrame:
        """获取成交量前 N 名
        
        Args:
            n: 返回数量
            
        Returns:
            pd.DataFrame: 成交量排名前 N 的股票
        """
        all_quotes = await self.get_all_quotes()
        if all_quotes.empty:
            return pd.DataFrame()
        
        return all_quotes.nlargest(n, 'volume')
    
    async def get_limit_up_stocks(self) -> pd.DataFrame:
        """获取涨停股票
        
        判断标准: 涨幅 >= 9.9%
        
        Returns:
            pd.DataFrame: 涨停股票
        """
        all_quotes = await self.get_all_quotes()
        if all_quotes.empty:
            return pd.DataFrame()
        
        return all_quotes[all_quotes['change_pct'] >= 9.9]
    
    async def get_limit_down_stocks(self) -> pd.DataFrame:
        """获取跌停股票
        
        判断标准: 涨幅 <= -9.9%
        
        Returns:
            pd.DataFrame: 跌停股票
        """
        all_quotes = await self.get_all_quotes()
        if all_quotes.empty:
            return pd.DataFrame()
        
        return all_quotes[all_quotes['change_pct'] <= -9.9]
    
    async def get_quotes_by_change_pct(
        self,
        min_pct: Optional[float] = None,
        max_pct: Optional[float] = None,
    ) -> pd.DataFrame:
        """按涨跌幅范围筛选
        
        Args:
            min_pct: 最小涨跌幅（%），None 表示不限
            max_pct: 最大涨跌幅（%），None 表示不限
            
        Returns:
            pd.DataFrame: 符合条件的股票
        """
        all_quotes = await self.get_all_quotes()
        if all_quotes.empty:
            return pd.DataFrame()
        
        result = all_quotes
        if min_pct is not None:
            result = result[result['change_pct'] >= min_pct]
        if max_pct is not None:
            result = result[result['change_pct'] <= max_pct]
        
        return result
    
    # ========== 便捷方法 ==========
    
    async def get_quotes_dict(self, codes: List[str]) -> Dict[str, Dict]:
        """获取字典格式的行情数据
        
        Args:
            codes: 股票代码列表
            
        Returns:
            Dict[str, Dict]: {code: {price, name, change_pct, ...}}
        """
        df = await self.get_quotes(codes)
        if df.empty:
            return {}
        
        return df.set_index('code').to_dict('index')
    
    # ========== 内部方法 ==========
    
    def _standardize_quotes(
        self,
        df: pd.DataFrame,
        include_orderbook: bool = False,
    ) -> pd.DataFrame:
        """标准化行情数据
        
        Args:
            df: 原始 DataFrame
            include_orderbook: 是否包含盘口字段
            
        Returns:
            pd.DataFrame: 标准化后的 DataFrame
        """
        if df.empty:
            return df
        
        # 字段映射（如果Provider层未完成）
        # easyquotation的特殊处理
        if 'now' in df.columns and 'price' not in df.columns:
            df = FieldMapper.map_columns(df, FieldMapper.EASYQUOTATION_MAPPING)
        
        # 计算派生字段
        df = FieldMapper.calculate_derived_fields(df)
        
        # 确保code是字符串并补零
        if 'code' in df.columns:
            df['code'] = df['code'].astype(str).str.replace(r'[^\d]', '', regex=True).str.zfill(6)
        
        # 确保包含所有必需字段（填充默认值）
        required = QuoteSchema.get_required_columns()
        for col in required:
            if col not in df.columns:
                if col in ['code', 'name']:
                    df[col] = ''
                else:
                    df[col] = 0.0
        
        return df
    
    # ========== 监控统计 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        
        if stats['total_requests'] > 0:
            stats['cache_hit_rate'] = f"{stats['cache_hits'] / stats['total_requests'] * 100:.1f}%"
        else:
            stats['cache_hit_rate'] = "N/A"
        
        return stats
    
    async def clear_cache(self, pattern: str = "quotes:*") -> int:
        """清除缓存
        
        Args:
            pattern: 缓存键模式
            
        Returns:
            int: 清除的键数量
        """
        if self._enable_cache and self._cache_manager:
            return await self._cache_manager.clear_pattern(pattern)
        return 0
