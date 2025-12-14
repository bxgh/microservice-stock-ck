# -*- coding: utf-8 -*-
"""
EPIC-007 分笔成交服务 (TickService)

提供统一的分笔成交数据查询接口，支持:
1. 当日/历史分笔数据查询
2. 大单筛选
3. 资金流向分析
4. 分时段资金统计

@author: EPIC-007 Story 007.02b
@date: 2025-12-07
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, date as date_type

import pandas as pd

from .cache_manager import CacheManager
from .schemas import TickSchema, CapitalFlowResult, FieldMapper
from .tick_analyzer import TickAnalyzer
from data_sources.providers import DataServiceManager, DataResult, DataType

logger = logging.getLogger(__name__)


class TickService:
    """分笔成交服务
    
    数据中台核心服务之一，为所有策略和应用提供统一的分笔数据接口。
    
    Features:
    - 当日/历史分笔查询
    - 多数据源降级 (mootdx → local_parquet → clickhouse)
    - 智能缓存 (当日盘中10min / 盘后1h / 历史1d)
    - 大单识别和资金流向分析
    - 分时段统计
    
    Example:
        service = TickService()
        await service.initialize()
        
        # 获取分笔数据
        ticks = await service.get_tick('000001', '2025-12-07')
        
        # 分析资金流向
        flow = await service.analyze_capital_flow('000001', '2025-12-07')
        
        # 筛选大单
        large_orders = await service.get_large_orders('000001', '2025-12-07')
        
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
            
            logger.info("Initializing TickService...")
            
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
            logger.info("✅ TickService initialized")
            return True
    
    async def close(self) -> None:
        """关闭服务"""
        if self._data_manager:
            await self._data_manager.close()
        
        if self._cache_manager:
            await self._cache_manager.close()
        
        self._initialized = False
        logger.info("TickService closed")
    
    # ========== 核心查询接口 ==========
    
    async def get_tick(
        self,
        code: str,
        date: str,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """获取分笔成交数据
        
        Args:
            code: 股票代码 (6位)
            date: 日期 (YYYY-MM-DD 或 YYYYMMDD)
                - 今天: 返回当日分笔（截止到现在）
                - 历史: 返回全天分笔
            use_cache: 是否使用缓存
            
        Returns:
            pd.DataFrame: 分笔数据
                - code: 股票代码
                - time: 成交时间 (HH:MM:SS)
                - price: 成交价格
                - volume: 成交量 (手)
                - amount: 成交额 (元)
                - direction: 买卖方向 (B/S/N)
                - tick_type: 成交类型 (0/1/2)
                
        Raises:
            ValueError: 参数错误
            RuntimeError: 所有数据源失败
        """
        if not code:
            raise ValueError("code cannot be empty")
        if not date:
            raise ValueError("date cannot be empty")
        
        self._stats['total_requests'] += 1
        
        # 标准化代码和日期
        code = code.replace('sz', '').replace('sh', '').zfill(6)
        date_str = date.replace('-', '')  # YYYYMMDD 格式
        
        # 生成缓存键
        cache_key = f"tick:{code}:{date_str}" if self._enable_cache else None
        
        # 确定缓存TTL
        ttl = self._get_tick_cache_ttl(date)
        
        # 尝试缓存
        if use_cache and self._enable_cache and cache_key:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                self._stats['cache_hits'] += 1
                logger.debug(f"Cache HIT for tick {code} {date_str}")
                return cached
            else:
                self._stats['cache_misses'] += 1
        
        # 使用循环爬取获取完整分笔数据
        self._stats['provider_calls'] += 1
        df = await self._fetch_full_tick_data(code, date_str)
        
        if df.empty:
            self._stats['failed_requests'] += 1
            raise RuntimeError(f"Failed to get tick data for {code} {date_str}")
        
        # 字段标准化
        df = self._standardize_tick(df, code)
        
        # 计算买卖方向
        df = TickAnalyzer.calculate_direction(df)
        
        # 缓存结果
        if use_cache and self._enable_cache and cache_key:
            await self._cache_manager.set(cache_key, df, ttl=ttl)
        
        logger.info(f"✅ Got {len(df)} ticks for {code} {date_str}")
        return df
    
    async def _fetch_full_tick_data(
        self,
        code: str,
        date_str: str,
    ) -> pd.DataFrame:
        """使用循环爬取策略获取完整分笔数据
        
        反向爬取策略: Start=0 为最新数据，递增 start 获取更早数据，
        直到到达开盘时间 (09:25) 或无更多数据。
        
        Args:
            code: 股票代码
            date_str: 日期 (YYYYMMDD)
            
        Returns:
            pd.DataFrame: 完整分笔数据
        """
        import asyncio
        
        # 获取 Provider
        tick_chain = self._data_manager._chains.get(DataType.TICK)
        if not tick_chain or not tick_chain.providers:
            logger.error("No TICK provider available")
            return pd.DataFrame()
        
        provider = tick_chain.providers[0]  # 使用第一个可用 Provider (mootdx)
        
        all_data = []
        seen_keys = set()
        
        current_start = 0
        batch_size = 800  # mootdx 每批最多返回800条
        max_empty_retries = 3
        empty_count = 0
        max_depth = 20000  # 安全限制
        
        logger.info(f"开始获取分笔数据: {code} {date_str} (反向爬取)")
        
        while current_start < max_depth:
            try:
                # 获取一批数据
                result = await provider.fetch(
                    DataType.TICK,
                    code=code,
                    date=date_str,
                    start=current_start,
                    count=batch_size
                )
                
                if not result.success or result.is_empty:
                    empty_count += 1
                    if empty_count >= max_empty_retries:
                        logger.debug(f"连续 {empty_count} 次空数据，停止获取")
                        break
                    current_start += batch_size
                    continue
                
                empty_count = 0
                batch_df = result.data
                
                if batch_df.empty:
                    break
                
                # 去重并添加数据
                for _, row in batch_df.iterrows():
                    # 使用 time+price+vol 作为唯一键
                    vol_col = 'vol' if 'vol' in batch_df.columns else 'volume'
                    key = f"{row['time']}_{row['price']}_{row[vol_col]}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_data.append(row)
                
                # 检查是否到达开盘时间
                times = batch_df['time'].astype(str).tolist()
                earliest_time = min(times)
                if earliest_time <= "09:25":
                    logger.debug(f"已到达开盘时间 ({earliest_time})，停止获取")
                    break
                
                current_start += batch_size
                await asyncio.sleep(0.05)  # 避免请求过快
                
            except Exception as e:
                logger.error(f"批次获取失败: {e}")
                break
        
        if not all_data:
            return pd.DataFrame()
        
        # 合并数据
        final_df = pd.DataFrame(all_data)
        
        # 按时间排序
        final_df = final_df.sort_values('time', ascending=True).reset_index(drop=True)
        
        logger.info(f"获取完成: {len(final_df)} 条分笔数据")
        return final_df
    
    async def get_tick_summary(
        self,
        code: str,
        date: str,
    ) -> Dict[str, Any]:
        """获取分笔统计摘要
        
        Args:
            code: 股票代码
            date: 日期
            
        Returns:
            Dict: 统计摘要
                - total_volume: 总成交量 (手)
                - total_amount: 总成交额 (元)
                - tick_count: 分笔笔数
                - avg_price: 均价
                - price_range: [最低价, 最高价]
                - total_buy_amount: 主动买入金额
                - total_sell_amount: 主动卖出金额
                - net_inflow: 净流入
                - large_order_count: 大单笔数
                - large_order_amount: 大单金额
        """
        # 获取分笔数据
        df = await self.get_tick(code, date)
        
        if df.empty:
            return {
                'total_volume': 0,
                'total_amount': 0,
                'tick_count': 0,
                'avg_price': 0,
                'price_range': [0, 0],
                'total_buy_amount': 0,
                'total_sell_amount': 0,
                'net_inflow': 0,
                'large_order_count': 0,
                'large_order_amount': 0,
            }
        
        # 基础统计
        summary = TickAnalyzer.get_tick_summary(df)
        
        # 资金流向
        buy_amount = df[df['direction'] == 'B']['amount'].sum()
        sell_amount = df[df['direction'] == 'S']['amount'].sum()
        net_inflow = buy_amount - sell_amount
        
        # 大单统计
        large_orders = TickAnalyzer.identify_large_orders(df, threshold=500_000)
        
        summary.update({
            'total_buy_amount': float(buy_amount),
            'total_sell_amount': float(sell_amount),
            'net_inflow': float(net_inflow),
            'large_order_count': len(large_orders),
            'large_order_amount': float(large_orders['amount'].sum() if not large_orders.empty else 0),
        })
        
        return summary
    
    async def get_large_orders(
        self,
        code: str,
        date: str,
        threshold: float = 500_000,
        direction: Optional[str] = None,
    ) -> pd.DataFrame:
        """筛选大单
        
        Args:
            code: 股票代码
            date: 日期
            threshold: 金额阈值（默认50万）
            direction: 方向过滤 ('B'/'S'/None)
            
        Returns:
            pd.DataFrame: 大单列表
                包含 order_level 列（超大单/大单/中单/小单）
        """
        # 获取分笔数据
        df = await self.get_tick(code, date)
        
        if df.empty:
            return pd.DataFrame()
        
        # 识别大单
        large_orders = TickAnalyzer.identify_large_orders(
            df,
            threshold=threshold,
            direction=direction
        )
        
        logger.info(f"Found {len(large_orders)} large orders for {code} {date} (threshold={threshold})")
        return large_orders
    
    async def analyze_capital_flow(
        self,
        code: str,
        date: str,
        large_threshold: float = 500_000,
    ) -> CapitalFlowResult:
        """分析资金流向
        
        Args:
            code: 股票代码
            date: 日期
            large_threshold: 大单阈值
            
        Returns:
            CapitalFlowResult: 资金流向分析结果
                - total_buy_amount: 总买入金额
                - total_sell_amount: 总卖出金额
                - net_inflow: 净流入
                - large_order_count: 大单笔数
                - large_order_amount: 大单总金额
                - buy_sell_ratio: 买卖比
                - time_analysis: 分时段分析
        """
        # 获取分笔数据
        df = await self.get_tick(code, date)
        
        # 计算资金流向
        flow = TickAnalyzer.calculate_capital_flow(
            df,
            code=code,
            date=date,
            large_threshold=large_threshold
        )
        
        logger.info(f"Capital flow analysis for {code} {date}: net_inflow={flow.net_inflow:,.0f}")
        return flow
    
    # ========== 内部方法 ==========
    
    def _standardize_tick(
        self,
        df: pd.DataFrame,
        code: str,
    ) -> pd.DataFrame:
        """标准化分笔数据
        
        Args:
            df: 原始 DataFrame
            code: 股票代码
            
        Returns:
            pd.DataFrame: 标准化后的 DataFrame
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # mootdx 返回的数据: time, price, vol, buyorsell, volume
        # vol 是成交量(手)，volume 也是成交量(手) - 两者相同
        # 先用 vol 计算 amount，再进行字段映射
        
        # 计算 amount (成交额) = price * vol * 100 (vol单位是手，1手=100股)
        if 'vol' in df.columns and 'price' in df.columns:
            df['amount'] = df['price'] * df['vol'] * 100
        elif 'volume' in df.columns and 'price' in df.columns:
            df['amount'] = df['price'] * df['volume'] * 100
        
        # 字段映射（mootdx 分笔数据: vol -> volume, type -> tick_type）
        if 'vol' in df.columns:
            # 删除可能存在的重复 volume 列，使用 vol 作为标准
            if 'volume' in df.columns:
                df = df.drop(columns=['volume'])
            df = FieldMapper.map_columns(df, FieldMapper.MOOTDX_TICK_MAPPING)
        
        # 添加 code 列
        if 'code' not in df.columns:
            df['code'] = code
        
        # 确保code是字符串并补零
        df['code'] = df['code'].astype(str).str.replace(r'[^\d]', '', regex=True).str.zfill(6)
        
        # 确保 time 列格式正确
        if 'time' in df.columns:
            # 如果是整数时间戳（09:30 = 930），转换为 HH:MM:SS
            if df['time'].dtype in ['int64', 'int32']:
                df['time'] = df['time'].apply(self._format_time)
        
        # 确保包含所有必需字段
        required = TickSchema.get_required_columns()
        for col in required:
            if col not in df.columns:
                if col == 'time':
                    df[col] = ''
                else:
                    df[col] = 0
        
        # 按时间排序
        if 'time' in df.columns:
            df = df.sort_values('time').reset_index(drop=True)
        
        return df
    
    def _format_time(self, time_int: int) -> str:
        """格式化时间
        
        Args:
            time_int: 整数时间 (930 = 09:30, 143000 = 14:30:00)
            
        Returns:
            str: HH:MM:SS 格式
        """
        time_str = str(time_int).zfill(6)
        if len(time_str) == 4:  # HHMM
            return f"{time_str[:2]}:{time_str[2:]}:00"
        elif len(time_str) == 6:  # HHMMSS
            return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
        else:
            return time_str
    
    def _get_tick_cache_ttl(self, date: str) -> int:
        """获取分笔数据缓存TTL
        
        Args:
            date: 日期 (YYYY-MM-DD)
            
        Returns:
            int: TTL (秒)
        """
        today = datetime.now().date().isoformat()
        
        if date == today:
            # 当日数据
            now_time = datetime.now().time()
            if now_time.hour < 15:
                # 盘中：10分钟
                return 600
            else:
                # 盘后：1小时
                return 3600
        else:
            # 历史数据：1天
            return 86400
    
    # ========== 监控统计 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        
        if stats['total_requests'] > 0:
            stats['cache_hit_rate'] = f"{stats['cache_hits'] / stats['total_requests'] * 100:.1f}%"
        else:
            stats['cache_hit_rate'] = "N/A"
        
        return stats
    
    async def clear_cache(self, code: Optional[str] = None, date: Optional[str] = None) -> int:
        """清除缓存
        
        Args:
            code: 股票代码（None=全部）
            date: 日期（None=全部）
            
        Returns:
            int: 清除的键数量
        """
        if not self._enable_cache or not self._cache_manager:
            return 0
        
        if code and date:
            pattern = f"tick:{code}:{date}"
        elif code:
            pattern = f"tick:{code}:*"
        else:
            pattern = "tick:*"
        
        return await self._cache_manager.clear_pattern(pattern)
