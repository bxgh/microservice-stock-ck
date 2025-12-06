# -*- coding: utf-8 -*-
"""
EPIC-007 Pywencai 数据提供者

基于 pywencai 库实现的数据提供者,支持:
- 自然语言选股 (SCREENING) - 独特能力
- 榜单数据 (RANKING) - 涨停池、龙虎榜等
- 板块数据 (SECTOR) - 行业/概念涨幅榜

@author: EPIC-007
@date: 2025-12-06
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import DataProvider, DataResult, DataType

logger = logging.getLogger(__name__)


class PywencaiProvider(DataProvider):
    """Pywencai 数据提供者
    
    使用同花顺 i问财 接口获取数据。
    
    独特能力:
    - 自然语言选股 (如 "今日涨停股票", "连续涨停天数大于2")
    - 板块涨幅榜 (行业/概念)
    
    优势:
    - 自然语言查询,灵活强大
    - 数据权威 (同花顺)
    - 支持复杂条件
    
    注意:
    - 需要 Node.js v16+ 环境
    - 响应时间较长 (5-15秒)
    """
    
    def __init__(
        self,
        perpage: int = 50,
        priority: Optional[Dict[DataType, int]] = None,
    ):
        """初始化
        
        Args:
            perpage: 每页结果数
            priority: 自定义优先级
        """
        self._perpage = perpage
        self._pw = None
        
        # 默认优先级
        self._priority = priority or {
            DataType.SCREENING: 1,  # 选股首选 (独特能力)
            DataType.RANKING: 2,    # 榜单备选
            DataType.SECTOR: 1,     # 板块首选
        }
    
    @property
    def name(self) -> str:
        return "pywencai"
    
    @property
    def capabilities(self) -> List[DataType]:
        return [DataType.SCREENING, DataType.RANKING, DataType.SECTOR]
    
    @property
    def priority_map(self) -> Dict[DataType, int]:
        return self._priority
    
    async def initialize(self) -> bool:
        """初始化"""
        try:
            import pywencai
            self._pw = pywencai
            logger.info("PywencaiProvider initialized")
            return True
        except ImportError as e:
            logger.error(f"PywencaiProvider initialization error: {e}")
            return False
    
    async def close(self) -> None:
        """关闭"""
        self._pw = None
        logger.info("PywencaiProvider closed")
    
    async def health_check(self) -> bool:
        """健康检查"""
        if self._pw is None:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            # 简单查询测试
            result = await loop.run_in_executor(
                None,
                lambda: self._pw.get(query="贵州茅台", perpage=1)
            )
            return result is not None
        except Exception as e:
            logger.warning(f"PywencaiProvider health check failed: {e}")
            return False
    
    async def fetch(self, data_type: DataType, **kwargs) -> DataResult:
        """获取数据"""
        if data_type == DataType.SCREENING:
            return await self._fetch_screening(**kwargs)
        elif data_type == DataType.RANKING:
            return await self._fetch_ranking(**kwargs)
        elif data_type == DataType.SECTOR:
            return await self._fetch_sector(**kwargs)
        else:
            return DataResult(
                success=False,
                error=f"Unsupported data type: {data_type.value}"
            )
    
    async def _ensure_pw(self) -> bool:
        """确保 pywencai 可用"""
        if self._pw is None:
            return await self.initialize()
        return True
    
    async def _query(self, query: str, perpage: Optional[int] = None) -> Optional[pd.DataFrame]:
        """执行查询"""
        if not await self._ensure_pw():
            return None
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._pw.get(query=query, perpage=perpage or self._perpage)
        )
        
        if hasattr(result, 'shape'):
            return result
        return None
    
    async def _fetch_screening(
        self,
        query: str,
        perpage: Optional[int] = None,
        **kwargs
    ) -> DataResult:
        """自然语言选股
        
        Args:
            query: 自然语言查询语句
                - "今日涨停股票"
                - "连续涨停天数大于2"
                - "市值小于50亿的科技股"
                - "近5日涨幅超过20%"
            perpage: 返回结果数量
        
        Returns:
            DataFrame 符合条件的股票列表
        """
        start_time = time.time()
        
        try:
            df = await self._query(query, perpage)
            latency_ms = (time.time() - start_time) * 1000
            
            if df is not None and len(df) > 0:
                return DataResult(
                    success=True,
                    data=df,
                    latency_ms=latency_ms,
                    extra={"query": query},
                )
            else:
                return DataResult(
                    success=False,
                    error=f"No result for query: {query}",
                    latency_ms=latency_ms,
                )
                
        except Exception as e:
            logger.error(f"PywencaiProvider screening error: {e}")
            return DataResult(
                success=False,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )
    
    async def _fetch_ranking(
        self,
        ranking_type: str = "limit_up",
        **kwargs
    ) -> DataResult:
        """获取榜单数据
        
        Args:
            ranking_type: 榜单类型
                - "limit_up": 涨停股票
                - "continuous_limit_up": 连板股
                - "dragon_tiger": 龙虎榜
        """
        start_time = time.time()
        
        # 查询语句映射
        query_map = {
            "limit_up": "今日涨停股票",
            "continuous_limit_up": "连续涨停天数大于1",
            "dragon_tiger": "今日上龙虎榜股票",
        }
        
        query = query_map.get(ranking_type)
        if not query:
            return DataResult(
                success=False,
                error=f"Unknown ranking type: {ranking_type}"
            )
        
        result = await self._fetch_screening(query=query, **kwargs)
        result.extra["ranking_type"] = ranking_type
        return result
    
    async def _fetch_sector(
        self,
        sector_type: str = "industry",
        **kwargs
    ) -> DataResult:
        """获取板块数据
        
        Args:
            sector_type: 板块类型
                - "industry": 行业涨幅榜
                - "concept": 概念涨幅榜
        """
        start_time = time.time()
        
        # 查询语句映射
        query_map = {
            "industry": "今日行业涨幅榜",
            "concept": "今日概念涨幅榜",
        }
        
        query = query_map.get(sector_type)
        if not query:
            return DataResult(
                success=False,
                error=f"Unknown sector type: {sector_type}"
            )
        
        result = await self._fetch_screening(query=query, **kwargs)
        result.extra["sector_type"] = sector_type
        return result
