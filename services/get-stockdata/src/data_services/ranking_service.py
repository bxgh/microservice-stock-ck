# -*- coding: utf-8 -*-
"""
EPIC-007 Story 007.03: RankingService - 榜单数据服务

提供统一的榜单数据接口，整合akshare标准化榜单和pywencai灵活查询。

核心功能:
- 6个标准榜单接口 (人气榜、飙升榜、盘口异动、涨停池、连板统计、龙虎榜)
- 2个自定义查询接口 (自然语言查询、高级筛选)
- 16种盘口异动类型支持
- 时段感知缓存策略 (盘中5分钟, 盘步1天)
- 双Provider降级链 (Akshare → Pywencai → Cache)

@author: EPIC-007 Story 007.03
@date: 2025-12-07
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd

from data_sources.providers import (
    DataServiceManager,
    DataResult,
    DataType,
)
from .cache_manager import CacheManager, TradingAwareTTL
from .schemas import (
    RankingItem,
    LimitUpItem,
    DragonTigerItem,
    AnomalyType,
    FieldMapper,
)

logger = logging.getLogger(__name__)


class RankingService:
    """榜单数据服务
    
    整合多数据源提供全面的榜单数据:
    - akshare: 16种标准异动类型 + 6种榜单
    - pywencai: 自然语言灵活查询
    - 时段感知缓存策略
    
    使用示例:
        >>> service = RankingService()
        >>> await service.initialize()
        
        >>> # 标准榜单查询
        >>> hot_stocks = await service.get_hot_rank(limit=50)
        >>> anomalies = await service.get_anomaly_stocks(AnomalyType.ROCKET_LAUNCH)
        
        >>> # 自定义查询
        >>> stocks = await service.query_anomaly("涨停且换手率>20%")
        
        >>> await service.close()
    """
    
    def __init__(
        self,
        enable_cache: bool = True,
        cache_manager: Optional[CacheManager] = None,
        data_service: Optional[DataServiceManager] = None,
    ):
        """初始化
        
        Args:
            enable_cache: 是否启用缓存
            cache_manager: 缓存管理器 (可选, 默认创建新实例)
            data_service: 数据服务管理器 (可选, 默认使用全局实例)
        """
        self._enable_cache = enable_cache
        self._cache = cache_manager or (CacheManager() if enable_cache else None)
        self._data_service = data_service
        
        # 时段感知TTL策略 (统一使用系统默认)
        self._ttl_strategy = TradingAwareTTL()
        
        # 静态TTL配置 (秒) - 用于盘后复盘数据
        self._static_ttl = {
            'limit_up_pool': 86400,      # 1天
            'continuous_limit_up': 86400, # 1天
            'dragon_tiger': 86400,        # 1天
        }
        
        logger.info(f"RankingService initialized (cache={'enabled' if enable_cache else 'disabled'})")
    
    async def initialize(self) -> bool:
        """初始化服务
        
        Returns:
            bool: 是否初始化成功
        """
        try:
            # 获取全局数据服务管理器 (需要await)
            if self._data_service is None:
                from data_sources.providers import get_data_service
                self._data_service = await get_data_service()
            
            # 初始化缓存
            if self._cache:
                await self._cache.initialize()
            
            logger.info("RankingService initialized successfully")
            return True
        except Exception as e:
            logger.error(f"RankingService initialization failed: {e}")
            return False
    
    async def close(self) -> None:
        """关闭服务"""
        if self._cache:
            await self._cache.close()
        logger.info("RankingService closed")
    
    # === 盘中实时榜单 ===
    
    async def get_hot_rank(self, limit: int = 100) -> List[RankingItem]:
        """获取人气榜 - 监控市场热度
        
        Args:
            limit: 返回数量 (默认100)
            
        Returns:
            List[RankingItem]: 按人气排序的股票列表
        """
        cache_key = f"ranking:hot_rank:{limit}"
        
        # 尝试缓存
        if self._enable_cache:
            cached = await self._get_cache(cache_key, 'hot_rank')
            if cached is not None:
                return cached
        
        # 从数据源获取
        result = await self._data_service.get_ranking(
            ranking_type='hot',
            limit=limit
        )
        
        if result.success and result.data is not None:
            items = await self._parse_to_ranking_items(result.data)
            items = items[:limit]  # 限制数量
            
            # 缓存
            if self._enable_cache:
                await self._set_cache(cache_key, items, 'hot_rank')
            
            logger.info(f"Retrieved {len(items)} hot rank stocks")
            return items
        
        logger.warning(f"Failed to get hot rank: {result.error}")
        return []
    
    async def get_surge_rank(self, limit: int = 100) -> List[RankingItem]:
        """获取飙升榜 - 捕捉热度突增
        
        Args:
            limit: 返回数量 (默认100)
            
        Returns:
            List[RankingItem]: 按热度飙升排序的股票列表
        """
        cache_key = f"ranking:surge_rank:{limit}"
        
        # 尝试缓存
        if self._enable_cache:
            cached = await self._get_cache(cache_key, 'surge_rank')
            if cached is not None:
                return cached
        
        # 从数据源获取
        result = await self._data_service.get_ranking(
            ranking_type='surge',
            limit=limit
        )
        
        if result.success and result.data is not None:
            items = await self._parse_to_ranking_items(result.data)
            items = items[:limit]
            
            # 缓存
            if self._enable_cache:
                await self._set_cache(cache_key, items, 'surge_rank')
            
            logger.info(f"Retrieved {len(items)} surge rank stocks")
            return items
        
        logger.warning(f"Failed to get surge rank: {result.error}")
        return []
    
    async def get_anomaly_stocks(
        self,
        anomaly_type: AnomalyType = AnomalyType.ROCKET_LAUNCH,
        limit: int = 100
    ) -> List[RankingItem]:
        """获取盘口异动股票 - 识别异常波动
        
        Args:
            anomaly_type: 异动类型 (默认火箭发射), 支持16种:
                - 上涨机会: 火箭发射、快速反弹、封涨停板、打开跌停板、触及涨停、
                           大笔买入、有大买盘、竞价上涨
                - 风险预警: 加速下跌、高台跳水、封跌停板、打开涨停板、触及跌停、
                           大笔卖出、有大卖盘、竞价下跌
                - 全部: 盘中异动
            limit: 返回数量 (默认100)
            
        Returns:
            List[RankingItem]: 异动股票列表
            
        Examples:
            >>> # 火箭发射
            >>> stocks = await service.get_anomaly_stocks(AnomalyType.ROCKET_LAUNCH)
            
            >>> # 大单买入
            >>> stocks = await service.get_anomaly_stocks(AnomalyType.LARGE_BUY)
        """
        cache_key = f"ranking:anomaly:{anomaly_type.value}:{limit}"
        
        # 尝试缓存
        if self._enable_cache:
            cached = await self._get_cache(cache_key, 'anomaly')
            if cached is not None:
                return cached
        
        # 从数据源获取 (akshare stock_changes_em需要symbol参数)
        result = await self._data_service.get_ranking(
            ranking_type='anomaly',
            symbol=anomaly_type.value,  # 传递异动类型给akshare
            limit=limit
        )
        
        if result.success and result.data is not None:
            items = await self._parse_to_ranking_items(result.data)
            items = items[:limit]
            
            # 缓存
            if self._enable_cache:
                await self._set_cache(cache_key, items, 'anomaly')
            
            logger.info(f"Retrieved {len(items)} anomaly stocks ({anomaly_type.value})")
            return items
        
        logger.warning(f"Failed to get anomaly stocks: {result.error}")
        return []
    
    # === 盘后复盘数据 ===
    
    async def get_limit_up_pool(self, date: str = None) -> List[LimitUpItem]:
        """获取涨停池 - 盘后复盘
        
        Args:
            date: 日期 (YYYYMMDD), None表示最新交易日
            
        Returns:
            List[LimitUpItem]: 涨停股票列表
        """
        date_str = date or datetime.now().strftime("%Y%m%d")
        cache_key = f"ranking:limit_up_pool:{date_str}"
        
        # 尝试缓存
        if self._enable_cache:
            cached = await self._get_cache(cache_key, 'limit_up_pool')
            if cached is not None:
                return cached
        
        # 从数据源获取
        result = await self._data_service.get_ranking(
            ranking_type='limit_up',
            date=date_str
        )
        
        if result.success and result.data is not None:
            items = await self._parse_to_limit_up_items(result.data)
            
            # 缓存
            if self._enable_cache:
                await self._set_cache(cache_key, items, 'limit_up_pool')
            
            logger.info(f"Retrieved {len(items)} limit up stocks for {date_str}")
            return items
        
        logger.warning(f"Failed to get limit up pool: {result.error}")
        return []
    
    async def get_continuous_limit_up(self, date: str = None) -> List[LimitUpItem]:
        """获取连板统计 - 连板高度分析
        
        Args:
            date: 日期 (YYYYMMDD), None表示最新交易日
            
        Returns:
            List[LimitUpItem]: 连板股票列表，按连板天数降序
        """
        date_str = date or datetime.now().strftime("%Y%m%d")
        cache_key = f"ranking:continuous_limit_up:{date_str}"
        
        # 尝试缓存
        if self._enable_cache:
            cached = await self._get_cache(cache_key, 'continuous_limit_up')
            if cached is not None:
                return cached
        
        # 从数据源获取
        result = await self._data_service.get_ranking(
            ranking_type='continuous_limit_up',
            date=date_str
        )
        
        if result.success and result.data is not None:
            items = await self._parse_to_limit_up_items(result.data)
            
            # 按连板天数降序排序
            items.sort(key=lambda x: x.continuous_days, reverse=True)
            
            # 缓存
            if self._enable_cache:
                await self._set_cache(cache_key, items, 'continuous_limit_up')
            
            logger.info(f"Retrieved {len(items)} continuous limit up stocks for {date_str}")
            return items
        
        logger.warning(f"Failed to get continuous limit up: {result.error}")
        return []
    
    async def get_dragon_tiger_list(self, date: str = None) -> List[DragonTigerItem]:
        """获取龙虎榜 - 主力动向追踪
        
        Args:
            date: 日期 (YYYYMMDD), None表示最新交易日
            
        Returns:
            List[DragonTigerItem]: 龙虎榜股票列表
        """
        date_str = date or datetime.now().strftime("%Y%m%d")
        cache_key = f"ranking:dragon_tiger:{date_str}"
        
        # 尝试缓存
        if self._enable_cache:
            cached = await self._get_cache(cache_key, 'dragon_tiger')
            if cached is not None:
                return cached
        
        # 从数据源获取
        result = await self._data_service.get_ranking(
            ranking_type='dragon_tiger',
            date=date_str
        )
        
        if result.success and result.data is not None:
            items = await self._parse_to_dragon_tiger_items(result.data)
            
            # 缓存
            if self._enable_cache:
                await self._set_cache(cache_key, items, 'dragon_tiger')
            
            logger.info(f"Retrieved {len(items)} dragon tiger stocks for {date_str}")
            return items
        
        logger.warning(f"Failed to get dragon tiger list: {result.error}")
        return []
    
    # === 自定义查询接口 (Pywencai) ===
    
    async def query_anomaly(
        self,
        query: str,
        limit: int = 100
    ) -> List[RankingItem]:
        """自定义异动查询 - 使用自然语言
        
        利用pywencai的NLP能力进行灵活查询。
        
        Args:
            query: 自然语言查询，例如:
                - "5分钟涨幅大于3%"
                - "涨停且换手率大于20%"
                - "连续涨停天数大于3天且市值小于100亿"
            limit: 返回数量 (默认100)
            
        Returns:
            List[RankingItem]: 匹配条件的股票列表
            
        Examples:
            >>> # 超级妖股筛选
            >>> stocks = await service.query_anomaly("连续涨停天数大于5天")
            
            >>> # 低位首板
            >>> stocks = await service.query_anomaly("首次涨停且换手率小于5%")
            
            >>> # 板块异动
            >>> stocks = await service.query_anomaly("人工智能概念涨停股票")
        """
        cache_key = f"ranking:custom:{hash(query)}:{limit}"
        
        # 尝试缓存
        if self._enable_cache:
            cached = await self._get_cache(cache_key, 'custom_query')
            if cached is not None:
                return cached
        
        # 使用 Pywencai 进行自然语言查询 (DataServiceManager.screen)
        result = await self._data_service.screen(
            query=query,
            perpage=limit
        )
        
        if result.success and result.data is not None:
            items = await self._parse_to_ranking_items(result.data)
            items = items[:limit]
            
            # 缓存
            if self._enable_cache:
                await self._set_cache(cache_key, items, 'custom_query')
            
            logger.info(f"Retrieved {len(items)} stocks via custom query: '{query}'")
            return items
        
        logger.warning(f"Failed custom query '{query}': {result.error}")
        return []
    
    async def advanced_screening(
        self,
        conditions: Dict[str, Any],
        limit: int = 100
    ) -> List[RankingItem]:
        """高级筛选 - 组合多个条件
        
        将条件字典转换为自然语言查询，然后使用pywencai查询。
        
        Args:
            conditions: 筛选条件字典，例如:
                {
                    'change_pct_min': 3.0,        # 最小涨幅
                    'turnover_rate_min': 10.0,    # 最小换手率
                    'continuous_days_min': 2,     # 最小连板天数
                    'sector': '人工智能',          # 限定板块
                    'market_cap_max': 100,        # 最大市值(亿)
                }
            limit: 返回数量 (默认100)
            
        Returns:
            List[RankingItem]: 匹配条件的股票列表
        """
        # 将条件转换为自然语言查询
        query_parts = []
        
        if 'change_pct_min' in conditions:
            query_parts.append(f"涨幅大于{conditions['change_pct_min']}%")
        if 'turnover_rate_min' in conditions:
            query_parts.append(f"换手率大于{conditions['turnover_rate_min']}%")
        if 'continuous_days_min' in conditions:
            query_parts.append(f"连续涨停天数大于{conditions['continuous_days_min']}")
        if 'sector' in conditions:
            query_parts.append(f"{conditions['sector']}概念")
        if 'market_cap_max' in conditions:
            query_parts.append(f"市值小于{conditions['market_cap_max']}亿")
        
        # 组合查询
        query = "且".join(query_parts)
        logger.debug(f"Advanced screening query: {query}")
        
        return await self.query_anomaly(query, limit)
    
    # === 内部方法 ===
    
    async def _get_cache(self, key: str, ttl_type: str) -> Optional[List]:
        """从缓存获取数据"""
        if not self._cache:
            return None
        
        try:
            return await self._cache.get(key)
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
            return None
    
    async def _set_cache(self, key: str, value: List, ttl_type: str) -> None:
        """设置缓存"""
        if not self._cache:
            return
        
        try:
            # 盘后复盘数据使用静态1天TTL
            if ttl_type in self._static_ttl:
                ttl = self._static_ttl[ttl_type]
            else:
                # 盘中数据使用时段感知策略
                ttl = self._ttl_strategy.get_ttl()
            
            await self._cache.set(key, value, ttl)
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
    
    async def _parse_to_ranking_items(self, df: pd.DataFrame) -> List[RankingItem]:
        """将DataFrame解析为RankingItem列表
        
        Args:
            df: 原始数据 (akshare或pywencai返回)
            
        Returns:
            List[RankingItem]: 标准化榜单项列表
        """
        if df is None or len(df) == 0:
            return []
        
        # 字段映射
        df_mapped = FieldMapper.map_columns(df, FieldMapper.AKSHARE_RANKING_MAPPING)
        
        # 确保必需字段存在
        items = []
        for idx, row in df_mapped.iterrows():
            try:
                item = RankingItem(
                    rank=row.get('rank', idx + 1),
                    code=str(row.get('code', '')).zfill(6),  # 补齐6位
                    name=row.get('name', ''),
                    change_pct=float(row.get('change_pct', 0.0)),
                    latest_price=float(row.get('latest_price', 0.0)),
                    volume=float(row.get('volume', 0.0)),
                    amount=float(row.get('amount', 0.0)),
                    score=row.get('score'),
                    turnover_rate=row.get('turnover_rate'),
                    metadata={k: v for k, v in row.items() if k not in RankingItem.__dataclass_fields__}
                )
                items.append(item)
            except Exception as e:
                logger.warning(f"Failed to parse row {idx}: {e}")
                continue
        
        return items
    
    async def _parse_to_limit_up_items(self, df: pd.DataFrame) -> List[LimitUpItem]:
        """将DataFrame解析为LimitUpItem列表"""
        ranking_items = await self._parse_to_ranking_items(df)
        
        # 转换为LimitUpItem
        df_mapped = FieldMapper.map_columns(df, FieldMapper.AKSHARE_RANKING_MAPPING)
        limit_up_items = []
        
        for idx, base_item in enumerate(ranking_items):
            try:
                row = df_mapped.iloc[idx]
                item = LimitUpItem.from_ranking_item(
                    base_item,
                    limit_up_time=row.get('limit_up_time', ''),
                    open_count=int(row.get('open_count', 0)),
                    continuous_days=int(row.get('continuous_days', 0)),
                    first_limit_up_time=row.get('first_limit_up_time'),
                    reason=row.get('reason'),
                )
                limit_up_items.append(item)
            except Exception as e:
                logger.warning(f"Failed to parse limit up item {idx}: {e}")
                continue
        
        return limit_up_items
    
    async def _parse_to_dragon_tiger_items(self, df: pd.DataFrame) -> List[DragonTigerItem]:
        """将DataFrame解析为DragonTigerItem列表"""
        ranking_items = await self._parse_to_ranking_items(df)
        
        # 转换为DragonTigerItem
        df_mapped = FieldMapper.map_columns(df, FieldMapper.AKSHARE_RANKING_MAPPING)
        dragon_tiger_items = []
        
        for idx, base_item in enumerate(ranking_items):
            try:
                row = df_mapped.iloc[idx]
                item = DragonTigerItem.from_ranking_item(
                    base_item,
                    net_amount=float(row.get('net_amount', 0.0)),
                    buy_amount=float(row.get('buy_amount', 0.0)),
                    sell_amount=float(row.get('sell_amount', 0.0)),
                    reason=row.get('reason', ''),
                    institution_count=int(row.get('institution_count', 0)),
                )
                dragon_tiger_items.append(item)
            except Exception as e:
                logger.warning(f"Failed to parse dragon tiger item {idx}: {e}")
                continue
        
        return dragon_tiger_items
