# -*- coding: utf-8 -*-
"""
EPIC-007 历史K线服务 (HistoryService)

提供统一的历史K线数据查询接口，支持:
1. 日线/周线/月线查询
2. 分钟线查询 (5/15/30/60分钟)
3. 复权处理 (前复权/后复权/不复权)
4. 丰富的字段 (涨跌幅/换手率/PE/PB)

数据源优先级:
1. baostock - 字段完整，支持复权
2. mootdx - 速度快，作为 fallback

@author: EPIC-007 Story 007.04
@date: 2025-12-07
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime, timedelta
from enum import Enum

import pandas as pd

from .cache_manager import CacheManager
from data_sources.providers import DataServiceManager, DataResult, DataType

logger = logging.getLogger(__name__)


class AdjustType(Enum):
    """复权类型"""
    NONE = "3"       # 不复权
    FORWARD = "2"    # 前复权 (用于看当前价格)
    BACKWARD = "1"   # 后复权 (用于计算收益率)


class Frequency(Enum):
    """K线周期"""
    DAILY = "d"      # 日线
    WEEKLY = "w"     # 周线  
    MONTHLY = "m"    # 月线
    MIN_5 = "5"      # 5分钟
    MIN_15 = "15"    # 15分钟
    MIN_30 = "30"    # 30分钟
    MIN_60 = "60"    # 60分钟


class HistoryService:
    """历史K线服务
    
    数据中台核心服务之一，为所有策略和应用提供统一的历史K线接口。
    
    Features:
    - 多周期支持 (日/周/月/分钟)
    - 复权支持 (前复权/后复权/不复权)
    - 丰富字段 (涨跌幅/换手率/PE/PB)
    - 多数据源降级 (baostock → mootdx)
    - 智能缓存
    
    Example:
        service = HistoryService()
        await service.initialize()
        
        # 获取日线 (默认前复权)
        df = await service.get_daily('600519', '2024-01-01', '2024-12-31')
        
        # 获取不复权日线
        df = await service.get_daily('600519', '2024-01-01', '2024-12-31', 
                                      adjust=AdjustType.NONE)
        
        # 获取5分钟线
        df = await service.get_minute('600519', '2024-12-01', '2024-12-05', freq=5)
        
        await service.close()
    """
    
    # 标准字段列表
    STANDARD_FIELDS = [
        'date', 'open', 'high', 'low', 'close', 'volume', 'amount',
        'pct_change', 'turnover', 'pe', 'pb'
    ]
    
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
        self._stats_lock = asyncio.Lock()  # 保护统计信息
        
        # 缓存 Provider 实例
        self._baostock_provider = None
        self._mootdx_provider = None
        
        # 统计信息
        self._stats: Dict[str, Any] = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'baostock_calls': 0,
            'mootdx_calls': 0,
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
            
            logger.info("Initializing HistoryService...")
            
            # 初始化数据管理器
            if self._data_manager is None:
                self._data_manager = DataServiceManager()
            
            if not await self._data_manager.initialize():
                logger.error("Failed to initialize DataServiceManager")
                return False
            
            # 初始化缓存管理器
            if self._enable_cache:
                if self._cache_manager is None:
                    self._cache_manager = CacheManager()
                
                if not await self._cache_manager.initialize():
                    logger.warning("Failed to initialize CacheManager, caching disabled")
                    self._enable_cache = False
            
            self._initialized = True
            logger.info("✅ HistoryService initialized")
            return True
    
    async def close(self) -> None:
        """关闭服务"""
        # 关闭 Provider 实例
        if self._baostock_provider:
            await self._baostock_provider.close()
            self._baostock_provider = None
        
        if self._mootdx_provider:
            await self._mootdx_provider.close()
            self._mootdx_provider = None
        
        if self._data_manager:
            await self._data_manager.close()
        
        if self._cache_manager:
            await self._cache_manager.close()
        
        self._initialized = False
        logger.info("HistoryService closed")
    
    async def _ensure_initialized(self) -> bool:
        """确保服务已初始化"""
        if not self._initialized:
            return await self.initialize()
        return True
    
    # ========== 核心查询接口 ==========
    
    async def get_daily(
        self,
        code: str,
        start_date: str,
        end_date: str,
        adjust: AdjustType = AdjustType.FORWARD,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """获取日线数据
        
        Args:
            code: 股票代码 (6位)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            adjust: 复权类型 (默认前复权)
            use_cache: 是否使用缓存
            
        Returns:
            pd.DataFrame: 日线数据
                - date: 日期
                - open/high/low/close: OHLC
                - volume: 成交量 (股)
                - amount: 成交额 (元)
                - pct_change: 涨跌幅 (%)
                - turnover: 换手率 (%)
                - pe: 市盈率 (TTM)
                - pb: 市净率 (MRQ)
                
        Raises:
            ValueError: 参数错误
            RuntimeError: 所有数据源失败
        """
        return await self._get_kline(
            code=code,
            start_date=start_date,
            end_date=end_date,
            frequency=Frequency.DAILY,
            adjust=adjust,
            use_cache=use_cache,
        )
    
    async def get_weekly(
        self,
        code: str,
        start_date: str,
        end_date: str,
        adjust: AdjustType = AdjustType.FORWARD,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """获取周线数据
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型
            use_cache: 是否使用缓存
            
        Returns:
            pd.DataFrame: 周线数据 (字段同日线)
        """
        return await self._get_kline(
            code=code,
            start_date=start_date,
            end_date=end_date,
            frequency=Frequency.WEEKLY,
            adjust=adjust,
            use_cache=use_cache,
        )
    
    async def get_monthly(
        self,
        code: str,
        start_date: str,
        end_date: str,
        adjust: AdjustType = AdjustType.FORWARD,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """获取月线数据
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型
            use_cache: 是否使用缓存
            
        Returns:
            pd.DataFrame: 月线数据 (字段同日线)
        """
        return await self._get_kline(
            code=code,
            start_date=start_date,
            end_date=end_date,
            frequency=Frequency.MONTHLY,
            adjust=adjust,
            use_cache=use_cache,
        )
    
    async def get_minute(
        self,
        code: str,
        start_date: str,
        end_date: str,
        freq: int = 5,
        adjust: AdjustType = AdjustType.FORWARD,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """获取分钟线数据
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            freq: 分钟周期 (5/15/30/60)
            adjust: 复权类型
            use_cache: 是否使用缓存
            
        Returns:
            pd.DataFrame: 分钟线数据
                - datetime: 日期时间
                - open/high/low/close: OHLC
                - volume: 成交量
                - amount: 成交额
        """
        freq_map = {
            5: Frequency.MIN_5,
            15: Frequency.MIN_15,
            30: Frequency.MIN_30,
            60: Frequency.MIN_60,
        }
        
        frequency = freq_map.get(freq)
        if not frequency:
            raise ValueError(f"Invalid frequency: {freq}, must be 5/15/30/60")
        
        return await self._get_kline(
            code=code,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjust=adjust,
            use_cache=use_cache,
        )
    
    # ========== 内部方法 ==========
    
    async def _get_kline(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: Frequency,
        adjust: AdjustType,
        use_cache: bool,
    ) -> pd.DataFrame:
        """获取K线数据 (内部方法)
        
        数据源优先级:
        1. baostock - 字段完整，支持复权
        2. mootdx - 速度快，作为 fallback
        """
        if not code:
            raise ValueError("code cannot be empty")
        if not start_date or not end_date:
            raise ValueError("start_date and end_date cannot be empty")
        
        # 确保已初始化
        if not await self._ensure_initialized():
            raise RuntimeError("HistoryService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 标准化代码
        code = code.replace('sz', '').replace('sh', '').replace('.', '').zfill(6)
        
        # 标准化日期
        start_date = start_date.replace('/', '-')
        end_date = end_date.replace('/', '-')
        
        # 生成缓存键
        cache_key = None
        if self._enable_cache and use_cache:
            cache_key = f"history:{code}:{frequency.value}:{adjust.value}:{start_date}:{end_date}"
            
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                logger.debug(f"Cache HIT for {cache_key}")
                return cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        # 尝试 baostock (优先)
        df = await self._fetch_from_baostock(code, start_date, end_date, frequency, adjust)
        
        if df is not None and not df.empty:
            async with self._stats_lock:
                self._stats['baostock_calls'] += 1
        else:
            # 降级到 mootdx
            logger.warning(f"Baostock failed for {code}, falling back to mootdx")
            df = await self._fetch_from_mootdx(code, start_date, end_date, frequency)
            
            if df is not None and not df.empty:
                async with self._stats_lock:
                    self._stats['mootdx_calls'] += 1
            else:
                async with self._stats_lock:
                    self._stats['failed_requests'] += 1
                raise RuntimeError(f"All providers failed for {code} {start_date}~{end_date}")
        
        # 标准化字段
        df = self._standardize_fields(df, code)
        
        # 缓存结果 (历史数据缓存1天)
        if cache_key and self._enable_cache:
            await self._cache_manager.set(cache_key, df, ttl=86400)
        
        logger.info(f"✅ Got {len(df)} bars for {code} ({frequency.value}) from {start_date} to {end_date}")
        return df
    
    async def _fetch_from_baostock(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: Frequency,
        adjust: AdjustType,
    ) -> Optional[pd.DataFrame]:
        """从 baostock 获取数据
        
        注意: baostock 需要通过 proxychains4 运行!
        """
        try:
            # 复用 Provider 实例
            if self._baostock_provider is None:
                from data_sources.providers.baostock_provider import BaostockProvider
                self._baostock_provider = BaostockProvider(priority={DataType.HISTORY: 1})
            
            if not await self._baostock_provider.initialize():
                logger.warning("BaostockProvider initialization failed")
                return None
            
            result = await self._baostock_provider.fetch(
                DataType.HISTORY,
                code=code,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency.value,
                adjustflag=adjust.value,
                # 请求完整字段
                fields="date,open,high,low,close,volume,amount,pctChg,turn,peTTM,pbMRQ",
            )
            
            if result.success and result.data is not None:
                return result.data
            else:
                logger.warning(f"Baostock fetch failed: {result.error}")
                return None
                
        except Exception as e:
            logger.error(f"Baostock error: {e}")
            return None
    
    async def _fetch_from_mootdx(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: Frequency,
    ) -> Optional[pd.DataFrame]:
        """从 mootdx 获取数据 (fallback)
        
        注意: mootdx 不支持复权，需要自己计算涨跌幅
        """
        try:
            # mootdx frequency 映射
            freq_map = {
                Frequency.DAILY: 9,
                Frequency.WEEKLY: 10,
                Frequency.MONTHLY: 11,
                Frequency.MIN_5: 8,
                Frequency.MIN_15: 7,
                Frequency.MIN_30: 6,
                Frequency.MIN_60: 5,
            }
            
            mootdx_freq = freq_map.get(frequency)
            if mootdx_freq is None:
                return None
            
            # 获取 mootdx provider
            from data_sources.providers.mootdx_provider import MootdxProvider
            
            provider = MootdxProvider()
            
            if not await provider.initialize():
                logger.warning("MootdxProvider initialization failed")
                return None
            
            try:
                # 计算需要获取的数据量 (根据日期范围估算)
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                days = (end_dt - start_dt).days + 1
                
                # 估算需要的条数
                if frequency == Frequency.DAILY:
                    count = min(days * 1.5, 5000)  # 日线
                elif frequency == Frequency.WEEKLY:
                    count = min(days // 5 * 1.5, 1000)  # 周线
                elif frequency == Frequency.MONTHLY:
                    count = min(days // 20 * 1.5, 500)  # 月线
                else:
                    count = min(days * 48 * 1.5, 10000)  # 分钟线
                
                # 分页获取
                all_data = []
                current_start = 0
                batch_size = 800
                
                while current_start < count:
                    result = await provider.fetch(
                        DataType.HISTORY,
                        code=code,
                        frequency=mootdx_freq,
                        start=current_start,
                        count=batch_size,
                    )
                    
                    if not result.success or result.data is None or result.data.empty:
                        break
                    
                    all_data.append(result.data)
                    current_start += batch_size
                    
                    # 检查是否已经超出日期范围
                    if 'datetime' in result.data.columns:
                        earliest = result.data['datetime'].min()
                        if pd.Timestamp(earliest) < pd.Timestamp(start_date):
                            break
                    
                    await asyncio.sleep(0.02)  # 避免请求过快
                
                if not all_data:
                    return None
                
                # 合并数据
                df = pd.concat(all_data, ignore_index=True)
                
                # 按日期筛选
                if 'datetime' in df.columns:
                    df['date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
                    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                
                return df
                
            finally:
                await provider.close()
                
        except Exception as e:
            logger.error(f"Mootdx error: {e}")
            return None
    
    def _standardize_fields(self, df: pd.DataFrame, code: str) -> pd.DataFrame:
        """标准化字段
        
        将不同数据源的字段统一为标准格式
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # 字段映射
        column_mapping = {
            # baostock 字段
            'pctChg': 'pct_change',
            'turn': 'turnover',
            'peTTM': 'pe',
            'pbMRQ': 'pb',
            # mootdx 字段
            'vol': 'volume',
            'datetime': 'date',
        }
        
        df = df.rename(columns=column_mapping)
        
        # 添加 code 列
        if 'code' not in df.columns:
            df['code'] = code
        
        # 确保数值列为 float
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 
                        'pct_change', 'turnover', 'pe', 'pb']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 如果没有涨跌幅，从 OHLC 计算
        if 'pct_change' not in df.columns or df['pct_change'].isna().all():
            if 'close' in df.columns:
                df['pct_change'] = df['close'].pct_change() * 100
        
        # 按日期排序
        if 'date' in df.columns:
            df = df.sort_values('date').reset_index(drop=True)
        
        return df
    
    # ========== 监控统计 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        
        if stats['total_requests'] > 0:
            stats['cache_hit_rate'] = f"{stats['cache_hits'] / stats['total_requests'] * 100:.1f}%"
            baostock_rate = stats['baostock_calls'] / (stats['baostock_calls'] + stats['mootdx_calls'] + 0.001) * 100
            stats['baostock_rate'] = f"{baostock_rate:.1f}%"
        else:
            stats['cache_hit_rate'] = "N/A"
            stats['baostock_rate'] = "N/A"
        
        return stats
    
    async def clear_cache(self, code: Optional[str] = None) -> int:
        """清除缓存
        
        Args:
            code: 股票代码（None=全部）
            
        Returns:
            int: 清除的键数量
        """
        if not self._enable_cache or not self._cache_manager:
            return 0
        
        if code:
            pattern = f"history:{code}:*"
        else:
            pattern = "history:*"
        
        return await self._cache_manager.clear_pattern(pattern)
