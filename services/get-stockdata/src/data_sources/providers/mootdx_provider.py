# -*- coding: utf-8 -*-
"""
EPIC-007 Mootdx 数据提供者

基于 mootdx 库实现的数据提供者,支持:
- 实时行情 (QUOTES)
- 分笔成交 (TICK)
- 历史K线 (HISTORY)

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


class MootdxProvider(DataProvider):
    """Mootdx 数据提供者
    
    使用通达信协议获取 A 股实时行情、分笔成交和历史K线。
    
    优势:
    - 速度快,延迟低
    - 数据稳定可靠
    - 支持批量查询
    
    注意:
    - 需要连接通达信服务器
    - bestip 会自动选择最佳服务器
    """
    
    def __init__(
        self,
        market: str = "std",
        timeout: int = 10,
        priority: Optional[Dict[DataType, int]] = None,
    ):
        """初始化
        
        Args:
            market: 市场类型 ("std" 标准/扩展)
            timeout: 超时时间 (秒)
            priority: 自定义优先级
        """
        self._market = market
        self._timeout = timeout
        self._client = None
        self._connection = None  # MootdxConnection 实例
        self._lock = asyncio.Lock()
        
        # 默认优先级
        self._priority = priority or {
            DataType.QUOTES: 1,   # 行情首选
            DataType.TICK: 1,     # 分笔首选
            DataType.HISTORY: 1,  # K线首选
        }
    
    @property
    def name(self) -> str:
        return "mootdx"
    
    @property
    def capabilities(self) -> List[DataType]:
        return [DataType.QUOTES, DataType.TICK, DataType.HISTORY]
    
    @property
    def priority_map(self) -> Dict[DataType, int]:
        return self._priority
    
    async def initialize(self) -> bool:
        """初始化连接"""
        try:
            # 使用 MootdxConnection 进行连接管理（包含 bestip、连接复用等）
            from ..mootdx.connection import MootdxConnection
            
            logger.info("Initializing MootdxProvider with MootdxConnection...")
            
            # 紧急修复: 禁用 bestip 以避免超时 (>3分钟)
            # TODO: 后续实现 bestip 超时保护机制
            self._connection = MootdxConnection(
                timeout=self._timeout,
                best_ip=False,  # 禁用 bestip，使用固定服务器
                connection_lifetime=300,  # 5分钟生命周期
                initial_wait_time=0.5,
                fixed_servers=[
                    '124.71.186.252:7727',  # 通达信服务器 1
                    '60.12.136.250:7727',   # 通达信服务器 2  
                    '114.80.63.12:7727',    # 通达信服务器 3
                ]
            )
            
            # 初始化并获取客户端
            if await self._connection.initialize():
                self._client = await self._connection.get_connection()
                if self._client:
                    logger.info("✅ MootdxProvider initialized successfully")
                    return True
            
            logger.error("❌ MootdxProvider initialization failed")
            return False
                
        except Exception as e:
            logger.error(f"MootdxProvider initialization error: {e}")
            return False
    
    async def close(self) -> None:
        """关闭连接"""
        if self._connection:
            await self._connection.close()
            self._connection = None
        self._client = None
        logger.info("MootdxProvider closed")
    
    async def health_check(self) -> bool:
        """健康检查"""
        if self._client is None:
            return False
        
        try:
            # 简单测试获取一只股票行情
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._client.quotes(symbol=['000001'])
            )
            return result is not None and len(result) > 0
        except Exception as e:
            logger.warning(f"MootdxProvider health check failed: {e}")
            return False
    
    async def fetch(self, data_type: DataType, **kwargs) -> DataResult:
        """获取数据"""
        if data_type == DataType.QUOTES:
            return await self._fetch_quotes(**kwargs)
        elif data_type == DataType.TICK:
            return await self._fetch_tick(**kwargs)
        elif data_type == DataType.HISTORY:
            return await self._fetch_history(**kwargs)
        else:
            return DataResult(
                success=False,
                error=f"Unsupported data type: {data_type.value}"
            )
    
    async def _ensure_client(self) -> bool:
        """确保客户端可用"""
        if self._client is None:
            return await self.initialize()
        return True
    
    async def _fetch_quotes(
        self,
        codes: List[str],
        **kwargs
    ) -> DataResult:
        """获取实时行情
        
        Args:
            codes: 股票代码列表, 如 ["000001", "600519"]
        
        Returns:
            DataFrame 包含: code, name, price, open, high, low, etc.
        """
        start_time = time.time()
        
        try:
            if not await self._ensure_client():
                return DataResult(success=False, error="Client not available")
            
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: self._client.quotes(symbol=codes)
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if df is not None and len(df) > 0:
                return DataResult(
                    success=True,
                    data=df,
                    latency_ms=latency_ms,
                )
            else:
                return DataResult(
                    success=False,
                    error="No data returned",
                    latency_ms=latency_ms,
                )
                
        except Exception as e:
            logger.error(f"MootdxProvider fetch quotes error: {e}")
            return DataResult(
                success=False,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )
    
    async def _fetch_tick(
        self,
        code: str,
        date: str = None,
        start: int = 0,
        count: int = 1000,
        **kwargs
    ) -> DataResult:
        """获取分笔成交数据
        
        支持两种模式:
        1. 历史分笔 (date != None): 获取指定日期的分笔数据
        2. 实时分笔 (date == None): 获取当日最新分笔 (仅盘中有效)
        
        Args:
            code: 股票代码
            date: 日期 (YYYY-MM-DD 或 YYYYMMDD)，None 表示实时分笔
            start: 起始位置 (0=最新)
            count: 获取数量
        
        Returns:
            DataFrame 包含: time, price, vol, buyorsell
        """
        start_time = time.time()
        
        try:
            if not await self._ensure_client():
                return DataResult(success=False, error="Client not available")
            
            loop = asyncio.get_event_loop()
            
            # 根据是否传入 date 参数，选择不同的获取方式
            if date:
                # 历史分笔模式: 传入 date 参数
                # 标准化日期格式: YYYY-MM-DD -> YYYYMMDD
                date_str = date.replace('-', '')
                
                df = await loop.run_in_executor(
                    None,
                    lambda: self._client.transactions(
                        symbol=code,
                        date=date_str,
                        start=start,
                        count=count
                    )
                )
                mode = f"历史分笔 ({date_str})"
            else:
                # 实时分笔模式: 不传 date，使用 offset
                df = await loop.run_in_executor(
                    None,
                    lambda: self._client.transactions(
                        symbol=code,
                        start=start,
                        offset=count
                    )
                )
                mode = "实时分笔"
            
            latency_ms = (time.time() - start_time) * 1000
            
            if df is not None and len(df) > 0:
                logger.debug(f"MootdxProvider {mode}: {len(df)} records")
                return DataResult(
                    success=True,
                    data=df,
                    latency_ms=latency_ms,
                )
            else:
                error_msg = f"No tick data ({mode})"
                if not date:
                    error_msg += " - possibly non-trading hours"
                return DataResult(
                    success=False,
                    error=error_msg,
                    latency_ms=latency_ms,
                )
                
        except Exception as e:
            logger.error(f"MootdxProvider fetch tick error: {e}")
            return DataResult(
                success=False,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )
    
    async def _fetch_history(
        self,
        code: str,
        frequency: int = 9,  # 9=日线, 8=5分钟, 7=15分钟, 6=30分钟, 5=60分钟
        count: int = 100,
        **kwargs
    ) -> DataResult:
        """获取历史K线数据
        
        Args:
            code: 股票代码
            frequency: K线周期 (9=日线, 8=5分钟, ...)
            count: 获取数量
        
        Returns:
            DataFrame 包含: open, high, low, close, vol, amount
        """
        start_time = time.time()
        
        try:
            if not await self._ensure_client():
                return DataResult(success=False, error="Client not available")
            
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: self._client.bars(symbol=code, frequency=frequency, offset=count)
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if df is not None and len(df) > 0:
                return DataResult(
                    success=True,
                    data=df,
                    latency_ms=latency_ms,
                )
            else:
                return DataResult(
                    success=False,
                    error="No history data",
                    latency_ms=latency_ms,
                )
                
        except Exception as e:
            logger.error(f"MootdxProvider fetch history error: {e}")
            return DataResult(
                success=False,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )
