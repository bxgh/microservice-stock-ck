# -*- coding: utf-8 -*-
"""
EPIC-007 板块数据服务 (SectorService)

提供行业/概念板块的涨幅排行、成分股查询、个股归属等功能。

核心功能:
1. 板块排行: 行业/概念涨幅榜
2. 成分股查询: 获取板块内所有股票
3. 个股归属: 查询股票所属板块
4. 热点发现: 综合热门板块

数据源: pywencai (自然语言查询)

@author: EPIC-007 Story 007.06
@date: 2025-12-07
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import pandas as pd

from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class SectorService:
    """板块数据服务
    
    提供行业/概念板块的涨幅排行、成分股查询、个股归属等功能。
    
    Example:
        service = SectorService()
        await service.initialize()
        
        # 板块排行
        industry_df = await service.get_industry_ranking(limit=20)
        concept_df = await service.get_concept_ranking(limit=20)
        
        # 成分股查询
        stocks = await service.get_sector_stocks('半导体')
        
        # 个股归属
        sectors = await service.get_stock_sectors('300750')
        
        await service.close()
    """
    
    # pywencai 查询模板
    QUERY_TEMPLATES = {
        'industry_ranking': '今日行业涨幅排行',
        'concept_ranking': '今日概念涨幅排行',
        'sector_stocks': '{sector_name}板块成分股',
        'stock_sectors': '{stock_name}所属板块',
    }
    
    # 默认配置
    DEFAULT_TIMEOUT = 30  # API 超时秒数
    
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
        
        # 检查 pywencai 依赖
        try:
            import pywencai
            self._pywencai = pywencai
        except ImportError as e:
            raise RuntimeError(f"pywencai dependency required: {e}")
        
        # 统计信息
        self._stats: Dict[str, Any] = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'pywencai_calls': 0,
            'timeout_errors': 0,
        }
    
    async def initialize(self) -> bool:
        """初始化服务"""
        async with self._lock:
            if self._initialized:
                return True
            
            logger.info("Initializing SectorService...")
            
            # 初始化缓存管理器
            if self._enable_cache:
                if self._cache_manager is None:
                    self._cache_manager = CacheManager()
                
                if not await self._cache_manager.initialize():
                    logger.warning("CacheManager init failed, caching disabled")
                    self._enable_cache = False
            
            self._initialized = True
            logger.info("✅ SectorService initialized")
            return True
    
    async def close(self) -> None:
        """关闭服务"""
        if self._cache_manager:
            await self._cache_manager.close()
        
        self._initialized = False
        logger.info("SectorService closed")
    
    async def _ensure_initialized(self) -> bool:
        """确保服务已初始化"""
        if not self._initialized:
            return await self.initialize()
        return True
    
    async def _query_pywencai(self, query: str, timeout: Optional[int] = None) -> Optional[pd.DataFrame]:
        """执行 pywencai 查询
        
        Args:
            query: 自然语言查询
            timeout: 超时时间(秒)，默认使用实例配置
            
        Returns:
            DataFrame or None
        """
        timeout = timeout or self._timeout
        
        try:
            async with self._stats_lock:
                self._stats['pywencai_calls'] += 1
            
            loop = asyncio.get_event_loop()
            
            # 使用 wait_for 实现超时控制
            df = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self._pywencai.get(query=query, loop=True)
                ),
                timeout=timeout
            )
            
            return df if df is not None and not df.empty else None
            
        except asyncio.TimeoutError:
            logger.error(f"pywencai query timeout ({timeout}s): {query}")
            async with self._stats_lock:
                self._stats['timeout_errors'] += 1
            return None
        except Exception as e:
            logger.error(f"pywencai query failed: {query}, error: {e}")
            return None
    
    # ========== 板块排行 ==========
    
    async def get_industry_ranking(
        self,
        limit: int = 50,
    ) -> pd.DataFrame:
        """行业板块涨跌幅排行
        
        Args:
            limit: 返回数量
            
        Returns:
            DataFrame:
                - sector_name: 行业名称
                - change_pct: 涨跌幅
                - leading_stock: 领涨股代码
                - leading_stock_name: 领涨股名称
        """
        if not await self._ensure_initialized():
            raise RuntimeError("SectorService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 缓存键
        cache_key = "sector:industry_ranking"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached.head(limit) if len(cached) > limit else cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        # 查询 pywencai
        query = self.QUERY_TEMPLATES['industry_ranking']
        df = await self._query_pywencai(query)
        
        if df is None:
            return pd.DataFrame()
        
        # 标准化字段
        df = self._standardize_ranking_data(df, 'industry')
        
        # 缓存 (5分钟)
        if self._enable_cache and not df.empty:
            await self._cache_manager.set(cache_key, df, ttl=300)
        
        return df.head(limit)
    
    async def get_concept_ranking(
        self,
        limit: int = 50,
    ) -> pd.DataFrame:
        """概念板块涨跌幅排行
        
        Args:
            limit: 返回数量
            
        Returns:
            DataFrame: 同 get_industry_ranking
        """
        if not await self._ensure_initialized():
            raise RuntimeError("SectorService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 缓存键
        cache_key = "sector:concept_ranking"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached.head(limit) if len(cached) > limit else cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        # 查询 pywencai
        query = self.QUERY_TEMPLATES['concept_ranking']
        df = await self._query_pywencai(query)
        
        if df is None:
            return pd.DataFrame()
        
        # 标准化字段
        df = self._standardize_ranking_data(df, 'concept')
        
        # 缓存 (5分钟)
        if self._enable_cache and not df.empty:
            await self._cache_manager.set(cache_key, df, ttl=300)
        
        return df.head(limit)
    
    def _standardize_ranking_data(
        self,
        df: pd.DataFrame,
        sector_type: str
    ) -> pd.DataFrame:
        """标准化排行数据"""
        if df is None or df.empty:
            return pd.DataFrame()
        
        try:
            # pywencai 返回的是个股数据，需要按行业/概念聚合
            # 字段: 股票代码, 股票简称, 涨跌幅, 行业简称/所属概念
            
            # 确定板块字段名
            sector_col = None
            for col in df.columns:
                if '行业' in col or '概念' in col:
                    sector_col = col
                    break
            
            if sector_col is None:
                # 如果没有板块字段，返回原始数据
                return df.head(50)
            
            # 确定涨跌幅字段
            change_col = None
            for col in df.columns:
                if '涨跌幅' in col:
                    change_col = col
                    break
            
            # 按板块分组，计算平均涨幅和领涨股
            result_data = []
            grouped = df.groupby(sector_col)
            
            for sector_name, group in grouped:
                if not sector_name or pd.isna(sector_name):
                    continue
                
                avg_change = group[change_col].mean() if change_col else 0
                
                # 找领涨股
                if change_col and len(group) > 0:
                    leader_idx = group[change_col].idxmax()
                    leader = group.loc[leader_idx]
                    leading_code = leader.get('股票代码', '')
                    leading_name = leader.get('股票简称', '')
                else:
                    leading_code = ''
                    leading_name = ''
                
                result_data.append({
                    'sector_name': str(sector_name).strip(),
                    'sector_type': sector_type,
                    'change_pct': round(avg_change, 2) if pd.notna(avg_change) else 0,
                    'leading_stock': str(leading_code).replace('.SZ', '').replace('.SH', ''),
                    'leading_stock_name': leading_name,
                    'stock_count': len(group),
                })
            
            result_df = pd.DataFrame(result_data)
            
            # 按涨幅排序
            if not result_df.empty:
                result_df = result_df.sort_values('change_pct', ascending=False)
                result_df = result_df.reset_index(drop=True)
            
            return result_df
            
        except Exception as e:
            logger.error(f"Standardize ranking data failed: {e}")
            return pd.DataFrame()
    
    # ========== 成分股查询 ==========
    
    async def get_sector_stocks(
        self,
        sector_name: str,
        sector_type: str = 'industry',
    ) -> List[str]:
        """获取板块成分股列表
        
        Args:
            sector_name: 板块名称 (如 '半导体', 'AI')
            sector_type: 板块类型 ('industry' | 'concept')
            
        Returns:
            List[str]: 成分股代码列表
        """
        if not await self._ensure_initialized():
            raise RuntimeError("SectorService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 缓存键
        cache_key = f"sector:stocks:{sector_name}"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        # 查询 pywencai
        query = self.QUERY_TEMPLATES['sector_stocks'].format(sector_name=sector_name)
        df = await self._query_pywencai(query)
        
        if df is None or df.empty:
            return []
        
        # 提取股票代码
        code_col = None
        for col in df.columns:
            if '代码' in col:
                code_col = col
                break
        
        if code_col is None:
            return []
        
        # 清理代码
        stocks = []
        for code in df[code_col].tolist():
            clean_code = str(code).replace('.SZ', '').replace('.SH', '').strip()
            if clean_code and len(clean_code) == 6:
                stocks.append(clean_code)
        
        # 缓存 (1天)
        if self._enable_cache and stocks:
            await self._cache_manager.set(cache_key, stocks, ttl=86400)
        
        logger.info(f"✅ Got {len(stocks)} stocks for sector {sector_name}")
        return stocks
    
    # ========== 个股归属 ==========
    
    async def get_stock_sectors(
        self,
        code: str,
    ) -> Dict[str, List[str]]:
        """获取个股所属板块
        
        Args:
            code: 股票代码
            
        Returns:
            Dict: {
                'industry': ['电力设备', '锂电池'],
                'concept': ['新能源', '储能', '碳中和']
            }
        """
        if not await self._ensure_initialized():
            raise RuntimeError("SectorService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 缓存键
        cache_key = f"sector:stock_sectors:{code}"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        result = {
            'industry': [],
            'concept': [],
        }
        
        # 查询 pywencai
        # 先获取股票简称用于查询
        query = f"{code}所属行业和概念"
        df = await self._query_pywencai(query)
        
        if df is not None and not df.empty:
            # 解析返回的板块信息
            for col in df.columns:
                col_lower = col.lower()
                if '行业' in col:
                    values = df[col].dropna().unique().tolist()
                    result['industry'].extend([str(v) for v in values if v])
                elif '概念' in col:
                    values = df[col].dropna().unique().tolist()
                    for v in values:
                        if v and isinstance(v, str):
                            # 概念可能是分号分隔的
                            concepts = v.replace('；', ';').split(';')
                            result['concept'].extend([c.strip() for c in concepts if c.strip()])
        
        # 去重
        result['industry'] = list(set(result['industry']))
        result['concept'] = list(set(result['concept']))
        
        # 缓存 (1天)
        if self._enable_cache:
            await self._cache_manager.set(cache_key, result, ttl=86400)
        
        return result
    
    # ========== 热点发现 ==========
    
    async def get_hot_sectors(
        self,
        top_n: int = 10,
    ) -> List[Dict]:
        """获取今日热门板块
        
        综合行业和概念，按涨幅排序
        
        Args:
            top_n: 返回数量
            
        Returns:
            List[Dict]: 热门板块列表
        """
        # 获取行业和概念排行
        industry_df = await self.get_industry_ranking(limit=top_n)
        concept_df = await self.get_concept_ranking(limit=top_n)
        
        hot_sectors = []
        
        # 合并行业
        if not industry_df.empty:
            for _, row in industry_df.iterrows():
                hot_sectors.append({
                    'sector_name': row.get('sector_name', ''),
                    'sector_type': 'industry',
                    'change_pct': row.get('change_pct', 0),
                    'leading_stock': row.get('leading_stock', ''),
                })
        
        # 合并概念
        if not concept_df.empty:
            for _, row in concept_df.iterrows():
                hot_sectors.append({
                    'sector_name': row.get('sector_name', ''),
                    'sector_type': 'concept',
                    'change_pct': row.get('change_pct', 0),
                    'leading_stock': row.get('leading_stock', ''),
                })
        
        # 按涨幅排序
        hot_sectors.sort(key=lambda x: x.get('change_pct', 0), reverse=True)
        
        return hot_sectors[:top_n]
    
    # ========== 监控统计 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        
        if stats['total_requests'] > 0:
            stats['cache_hit_rate'] = f"{stats['cache_hits'] / stats['total_requests'] * 100:.1f}%"
        else:
            stats['cache_hit_rate'] = "N/A"
        
        return stats
