# -*- coding: utf-8 -*-
"""
EPIC-007 指数与ETF服务 (IndexService)

提供统一的指数与ETF数据查询接口，采用三层架构:
1. Tier 1: 基准指数 (固定) - 策略对标、风格归因
2. Tier 2: 动态热点 (实时) - 热点追踪、资金流向
3. Tier 3: 灵活扩展 (按需) - 任意查询

数据源:
- akshare: 指数成分股、ETF持仓
- mootdx: ETF实时行情
- pywencai: 热门主题识别

@author: EPIC-007 Story 007.05
@date: 2025-12-07
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import pandas as pd

from .cache_manager import CacheManager
from ..data_sources.providers import DataServiceManager, DataType

logger = logging.getLogger(__name__)


class IndexService:
    """指数与ETF服务
    
    三层架构设计:
    - Tier 1: 11个基准指数 (策略对标)
    - Tier 2: ETF热点排行 (动态追踪)
    - Tier 3: 任意查询 (灵活扩展)
    
    Example:
        service = IndexService()
        await service.initialize()
        
        # Tier 1: 基准指数
        benchmarks = service.get_benchmark_list()
        constituents = await service.get_constituents('000300')
        
        # Tier 2: 动态热点
        hot_etfs = await service.get_hot_etf_ranking(top_n=20)
        
        # Tier 3: 任意查询
        holdings = await service.get_etf_holdings('510300')
        
        await service.close()
    """
    
    # Tier 1: 基准指数配置
    BENCHMARK_INDICES = {
        # 宽基指数
        '000300': '沪深300',        # 大盘核心基准
        '000905': '中证500',        # 中盘基准
        '000852': '中证1000',       # 小盘基准
        '000016': '上证50',         # 超大蓝筹
        '000985': '中证全指',       # 全市场
        '399006': '创业板指',       # 创业板
        '000688': '科创50',         # 科创板
        '899050': '北证50',         # 北交所
        # 风格因子
        '000922': '中证红利',       # 红利因子
        '000918': '沪深300成长',    # 成长风格
        '000919': '沪深300价值',    # 价值风格
    }
    
    # 主流 ETF 代码前缀
    ETF_PREFIXES = ('510', '511', '512', '513', '515', '516', '517', '518', '588', '159')
    
    def __init__(
        self,
        data_manager: Optional[DataServiceManager] = None,
        cache_manager: Optional[CacheManager] = None,
        enable_cache: bool = True,
    ):
        """初始化"""
        self._data_manager = data_manager
        self._cache_manager = cache_manager
        self._enable_cache = enable_cache
        
        self._initialized = False
        self._lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
        self._provider_lock = asyncio.Lock()  # 保护 Provider 初始化
        
        # 缓存 Provider 实例
        self._mootdx_provider = None
        
        # 统计信息
        self._stats: Dict[str, Any] = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
        }
    
    async def initialize(self) -> bool:
        """初始化服务"""
        async with self._lock:
            if self._initialized:
                return True
            
            logger.info("Initializing IndexService...")
            
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
            logger.info("✅ IndexService initialized")
            return True
    
    async def close(self) -> None:
        """关闭服务"""
        if self._mootdx_provider:
            await self._mootdx_provider.close()
            self._mootdx_provider = None
        
        if self._data_manager:
            await self._data_manager.close()
        
        if self._cache_manager:
            await self._cache_manager.close()
        
        self._initialized = False
        logger.info("IndexService closed")
    
    async def _ensure_initialized(self) -> bool:
        """确保服务已初始化"""
        if not self._initialized:
            return await self.initialize()
        return True
    
    # ========== Tier 1: 基准指数 ==========
    
    def get_benchmark_list(self) -> Dict[str, str]:
        """获取基准指数列表
        
        Returns:
            Dict: {代码: 名称}
        """
        return self.BENCHMARK_INDICES.copy()
    
    async def get_constituents(self, index_code: str) -> List[str]:
        """获取指数成分股列表
        
        Args:
            index_code: 指数代码 (如 '000300')
            
        Returns:
            List[str]: 成分股代码列表
        """
        if not await self._ensure_initialized():
            raise RuntimeError("IndexService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 缓存键
        cache_key = f"index:constituents:{index_code}"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        try:
            import akshare as ak
            
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: ak.index_stock_cons(symbol=index_code)
            )
            
            if df is not None and not df.empty:
                # 提取成分股代码
                code_col = '品种代码' if '品种代码' in df.columns else df.columns[0]
                constituents = df[code_col].tolist()
                
                # 缓存 (1天)
                if self._enable_cache:
                    await self._cache_manager.set(cache_key, constituents, ttl=86400)
                
                logger.info(f"✅ Got {len(constituents)} constituents for {index_code}")
                return constituents
            else:
                logger.warning(f"No constituents for {index_code}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get constituents for {index_code}: {e}")
            return []
    
    async def get_index_weights(self, index_code: str) -> pd.DataFrame:
        """获取指数成分股权重
        
        注意: akshare 的 index_stock_cons 不含权重，
        需要从 ETF 持仓反推权重 (如 510300 反推沪深300权重)
        
        Args:
            index_code: 指数代码
            
        Returns:
            DataFrame: 含权重的成分股数据
        """
        # 指数代码到对应ETF的映射
        index_to_etf = {
            '000300': '510300',  # 沪深300 -> 华泰柏瑞沪深300ETF
            '000905': '510500',  # 中证500 -> 南方中证500ETF
            '399006': '159915',  # 创业板 -> 易方达创业板ETF
        }
        
        etf_code = index_to_etf.get(index_code)
        if not etf_code:
            logger.warning(f"No ETF mapping for index {index_code}")
            return pd.DataFrame()
        
        # 获取 ETF 持仓作为权重参考
        return await self.get_etf_holdings(etf_code)
    
    # ========== Tier 2: 动态热点 ==========
    
    async def get_hot_etf_ranking(self, top_n: int = 20) -> pd.DataFrame:
        """获取 ETF 成交额排行
        
        反映当日市场热点方向
        
        Args:
            top_n: 返回数量
            
        Returns:
            DataFrame: ETF 排行
                - code: 代码
                - name: 名称
                - price: 最新价
                - change_pct: 涨跌幅
                - turnover: 成交额
        """
        if not await self._ensure_initialized():
            raise RuntimeError("IndexService not initialized")
        
        try:
            # 使用锁保护 Provider 初始化
            async with self._provider_lock:
                if self._mootdx_provider is None:
                    from ..data_sources.providers.mootdx_provider import MootdxProvider
                    self._mootdx_provider = MootdxProvider()
                    await self._mootdx_provider.initialize()
            
            # 获取主流 ETF 列表
            etf_codes = await self._get_etf_code_list()
            
            if not etf_codes:
                logger.warning("No ETF codes available")
                return pd.DataFrame()
            
            # 批量获取行情
            result = await self._mootdx_provider.fetch(
                DataType.QUOTES,
                codes=etf_codes[:100],  # 限制数量
            )
            
            if not result.success or result.data is None:
                return pd.DataFrame()
            
            df = result.data
            
            # 标准化字段
            df = df.rename(columns={
                'code': 'code',
                'name': 'name',
                'price': 'price',
                'amount': 'turnover',
            })
            
            # 计算涨跌幅
            if 'open' in df.columns and 'price' in df.columns:
                df['change_pct'] = (df['price'] / df['open'] - 1) * 100
            else:
                df['change_pct'] = 0
            
            # 按成交额排序
            df = df.sort_values('turnover', ascending=False).head(top_n)
            
            # 选择需要的字段
            columns = ['code', 'name', 'price', 'change_pct', 'turnover']
            columns = [c for c in columns if c in df.columns]
            
            return df[columns].reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"Failed to get hot ETF ranking: {e}")
            return pd.DataFrame()
    
    async def get_trending_themes(self) -> List[Dict]:
        """获取热门主题
        
        通过分析 ETF 涨幅识别当前热门主题
        
        Returns:
            List[Dict]: 热门主题列表
                - theme: 主题名称
                - change_pct: 涨跌幅
                - etf_code: 代表 ETF
        """
        try:
            # 获取 ETF 行情
            etf_ranking = await self.get_hot_etf_ranking(top_n=50)
            
            if etf_ranking.empty:
                return []
            
            # 按涨幅排序提取热门主题
            if 'change_pct' in etf_ranking.columns:
                top_gainers = etf_ranking.sort_values('change_pct', ascending=False).head(10)
                
                themes = []
                for _, row in top_gainers.iterrows():
                    themes.append({
                        'theme': row.get('name', ''),
                        'change_pct': row.get('change_pct', 0),
                        'etf_code': row.get('code', ''),
                    })
                
                return themes
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get trending themes: {e}")
            return []
    
    async def _get_etf_code_list(self) -> List[str]:
        """获取 ETF 代码列表
        
        从缓存或生成主流 ETF 列表
        """
        # 主流 ETF 列表 (硬编码常用的)
        common_etfs = [
            # 宽基
            '510300', '510500', '510050', '159915', '159919',
            '512100', '588000', '588050',
            # 行业
            '512480', '512660', '512690', '515030', '515050',
            '512010', '512800', '515880', '516160', '512980',
            '512760', '512880', '515790', '512200', '512400',
            # 主题
            '513050', '513100', '513180', '159920', '510900',
        ]
        return common_etfs
    
    # ========== Tier 3: 灵活扩展 ==========
    
    async def get_etf_holdings(
        self,
        etf_code: str,
        year: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取 ETF 持仓明细
        
        Args:
            etf_code: ETF 代码 (如 '510300')
            year: 年份 (默认当年)
            
        Returns:
            DataFrame: 持仓数据
                - stock_code: 股票代码
                - stock_name: 股票名称
                - weight: 占净值比例
                - shares: 持股数
                - value: 持仓市值
        """
        if not await self._ensure_initialized():
            raise RuntimeError("IndexService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        year = year or str(datetime.now().year)
        
        # 缓存键
        cache_key = f"etf:holdings:{etf_code}:{year}"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        try:
            import akshare as ak
            
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: ak.fund_portfolio_hold_em(symbol=etf_code, date=year)
            )
            
            if df is not None and not df.empty:
                # 标准化字段
                df = df.rename(columns={
                    '股票代码': 'stock_code',
                    '股票名称': 'stock_name',
                    '占净值比例': 'weight',
                    '持股数': 'shares',
                    '持仓市值': 'value',
                })
                
                # 缓存 (1天)
                if self._enable_cache:
                    await self._cache_manager.set(cache_key, df, ttl=86400)
                
                logger.info(f"✅ Got {len(df)} holdings for ETF {etf_code}")
                return df
            else:
                logger.warning(f"No holdings for ETF {etf_code}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Failed to get ETF holdings for {etf_code}: {e}")
            return pd.DataFrame()
    
    def search_index(self, keyword: str) -> List[Dict]:
        """搜索指数/ETF
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            List[Dict]: 匹配结果
        """
        results = []
        
        # 搜索基准指数
        for code, name in self.BENCHMARK_INDICES.items():
            if keyword in code or keyword in name:
                results.append({
                    'code': code,
                    'name': name,
                    'type': 'index',
                })
        
        return results
    
    # ========== 监控统计 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        
        if stats['total_requests'] > 0:
            stats['cache_hit_rate'] = f"{stats['cache_hits'] / stats['total_requests'] * 100:.1f}%"
        else:
            stats['cache_hit_rate'] = "N/A"
        
        return stats
    
    async def clear_cache(self, pattern: str = "index:*") -> int:
        """清除缓存"""
        if not self._enable_cache or not self._cache_manager:
            return 0
        
        return await self._cache_manager.clear_pattern(pattern)
