# -*- coding: utf-8 -*-
"""
EPIC-007 Akshare 数据提供者

基于 akshare 库实现的数据提供者,支持:
- 榜单数据 (RANKING) - 涨停池、龙虎榜、人气榜
- 指数成分 (INDEX) - 沪深300、中证500等

@author: EPIC-007
@date: 2025-12-06
"""

import asyncio
import logging
import time
from datetime import datetime, date
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import DataProvider, DataResult, DataType

logger = logging.getLogger(__name__)


class AkshareProvider(DataProvider):
    """Akshare 数据提供者
    
    使用 akshare 获取榜单数据和指数成分。
    
    优势:
    - 数据丰富,覆盖面广
    - 东方财富数据源,权威可靠
    - 免费无限制
    
    注意:
    - 部分 API 可能被反爬虫拦截
    - 榜单数据非交易日可能为空
    """
    
    def __init__(
        self,
        priority: Optional[Dict[DataType, int]] = None,
    ):
        """初始化
        
        Args:
            priority: 自定义优先级
        """
        self._ak = None
        
        # 默认优先级
        self._priority = priority or {
            DataType.RANKING: 1,  # 榜单首选
            DataType.INDEX: 1,    # 指数首选
        }
    
    @property
    def name(self) -> str:
        return "akshare"
    
    @property
    def capabilities(self) -> List[DataType]:
        return [DataType.RANKING, DataType.INDEX]
    
    @property
    def priority_map(self) -> Dict[DataType, int]:
        return self._priority
    
    async def initialize(self) -> bool:
        """初始化"""
        try:
            import akshare as ak
            self._ak = ak
            logger.info("AkshareProvider initialized")
            return True
        except ImportError as e:
            logger.error(f"AkshareProvider initialization error: {e}")
            return False
    
    async def close(self) -> None:
        """关闭"""
        self._ak = None
        logger.info("AkshareProvider closed")
    
    async def health_check(self) -> bool:
        """健康检查"""
        if self._ak is None:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            # 用人气榜测试,基本不会被拦截
            result = await loop.run_in_executor(
                None,
                self._ak.stock_hot_rank_em
            )
            return result is not None and len(result) > 0
        except Exception as e:
            logger.warning(f"AkshareProvider health check failed: {e}")
            return False
    
    async def fetch(self, data_type: DataType, **kwargs) -> DataResult:
        """获取数据"""
        if data_type == DataType.RANKING:
            return await self._fetch_ranking(**kwargs)
        elif data_type == DataType.INDEX:
            return await self._fetch_index(**kwargs)
        else:
            return DataResult(
                success=False,
                error=f"Unsupported data type: {data_type.value}"
            )
    
    async def _ensure_ak(self) -> bool:
        """确保 akshare 可用"""
        if self._ak is None:
            return await self.initialize()
        return True
    
    async def _fetch_ranking(
        self,
        ranking_type: str = "hot",
        date_str: Optional[str] = None,
        **kwargs
    ) -> DataResult:
        """获取榜单数据
        
        Args:
            ranking_type: 榜单类型
                - "hot": 人气榜
                - "surge": 飙升榜
                - "limit_up": 涨停池
                - "continuous_limit_up": 连板统计
                - "dragon_tiger": 龙虎榜
                - "anomaly": 盘口异动
            date_str: 日期 (YYYYMMDD), 默认今天
        
        Returns:
            DataFrame
        """
        start_time = time.time()
        
        try:
            if not await self._ensure_ak():
                return DataResult(success=False, error="Akshare not available")
            
            today = date_str or datetime.now().strftime("%Y%m%d")
            loop = asyncio.get_event_loop()
            
            # 根据类型选择 API
            api_map = {
                "hot": lambda: self._ak.stock_hot_rank_em(),
                "surge": lambda: self._ak.stock_hot_up_em(),
                "anomaly": lambda: self._ak.stock_changes_em(),
                "limit_up": lambda: self._ak.stock_zt_pool_em(date=today),
                "continuous_limit_up": lambda: self._ak.stock_zt_pool_strong_em(date=today),
                "dragon_tiger": lambda: self._ak.stock_lhb_detail_em(
                    start_date=today, end_date=today
                ),
            }
            
            api_func = api_map.get(ranking_type)
            if not api_func:
                return DataResult(
                    success=False,
                    error=f"Unknown ranking type: {ranking_type}"
                )
            
            df = await loop.run_in_executor(None, api_func)
            latency_ms = (time.time() - start_time) * 1000
            
            if df is not None and len(df) > 0:
                return DataResult(
                    success=True,
                    data=df,
                    latency_ms=latency_ms,
                    extra={"ranking_type": ranking_type, "date": today},
                )
            else:
                return DataResult(
                    success=False,
                    error=f"No {ranking_type} data (possibly non-trading day)",
                    latency_ms=latency_ms,
                )
                
        except Exception as e:
            logger.error(f"AkshareProvider fetch ranking error: {e}")
            return DataResult(
                success=False,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )
    
    async def _fetch_index(
        self,
        index_code: str = "000300",
        **kwargs
    ) -> DataResult:
        """获取指数成分股
        
        Args:
            index_code: 指数代码
                - "000300": 沪深300
                - "000905": 中证500
                - "000016": 上证50
        
        Returns:
            DataFrame 包含成分股列表
        """
        start_time = time.time()
        
        try:
            if not await self._ensure_ak():
                return DataResult(success=False, error="Akshare not available")
            
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: self._ak.index_stock_cons(symbol=index_code)
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if df is not None and len(df) > 0:
                return DataResult(
                    success=True,
                    data=df,
                    latency_ms=latency_ms,
                    extra={"index_code": index_code},
                )
            else:
                return DataResult(
                    success=False,
                    error=f"No index data for {index_code}",
                    latency_ms=latency_ms,
                )
                
        except Exception as e:
            logger.error(f"AkshareProvider fetch index error: {e}")
            return DataResult(
                success=False,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )
