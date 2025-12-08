# -*- coding: utf-8 -*-
"""
EPIC-007 Easyquotation 数据提供者

基于 easyquotation 库实现的数据提供者,支持:
- 实时行情 (QUOTES) - 多源: sina/tencent

作为 mootdx 的备份数据源。

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


class EasyquotationProvider(DataProvider):
    """Easyquotation 数据提供者
    
    使用新浪/腾讯行情接口获取 A 股实时行情。
    
    优势:
    - 支持全市场快照 (5000+只股票)
    - 多数据源可选 (sina/tencent)
    - 无需登录,简单稳定
    
    注意:
    - 只支持实时行情,不支持分笔和K线
    - 作为 mootdx 的备份数据源
    """
    
    def __init__(
        self,
        source: str = "sina",
        priority: Optional[Dict[DataType, int]] = None,
    ):
        """初始化
        
        Args:
            source: 数据源 ("sina" 或 "tencent")
            priority: 自定义优先级
        """
        self._source = source
        self._quotation = None
        
        # 默认优先级 (作为备选)
        self._priority = priority or {
            DataType.QUOTES: 2,  # 行情备选
        }
    
    @property
    def name(self) -> str:
        return "easyquotation"
    
    @property
    def capabilities(self) -> List[DataType]:
        return [DataType.QUOTES]
    
    @property
    def priority_map(self) -> Dict[DataType, int]:
        return self._priority
    
    async def initialize(self) -> bool:
        """初始化"""
        try:
            import easyquotation
            
            loop = asyncio.get_event_loop()
            self._quotation = await loop.run_in_executor(
                None,
                lambda: easyquotation.use(self._source)
            )
            
            logger.info(f"EasyquotationProvider initialized with source: {self._source}")
            return True
            
        except Exception as e:
            logger.error(f"EasyquotationProvider initialization error: {e}")
            return False
    
    async def close(self) -> None:
        """关闭"""
        self._quotation = None
        logger.info("EasyquotationProvider closed")
    
    async def health_check(self) -> bool:
        """健康检查"""
        if self._quotation is None:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._quotation.real(['000001'])
            )
            return result is not None and len(result) > 0
        except Exception as e:
            logger.warning(f"EasyquotationProvider health check failed: {e}")
            return False
    
    async def fetch(self, data_type: DataType, **kwargs) -> DataResult:
        """获取数据"""
        if data_type == DataType.QUOTES:
            return await self._fetch_quotes(**kwargs)
        else:
            return DataResult(
                success=False,
                error=f"Unsupported data type: {data_type.value}"
            )
    
    async def _ensure_quotation(self) -> bool:
        """确保 quotation 可用"""
        if self._quotation is None:
            return await self.initialize()
        return True
    
    async def _fetch_quotes(
        self,
        codes: Optional[List[str]] = None,
        all_market: bool = False,
        **kwargs
    ) -> DataResult:
        """获取实时行情
        
        Args:
            codes: 股票代码列表, 如 ["000001", "600519"]
            all_market: 是否获取全市场行情
        
        Returns:
            DataFrame 包含: code, name, now(价格), open, high, low, etc.
        """
        start_time = time.time()
        
        try:
            if not await self._ensure_quotation():
                return DataResult(success=False, error="Quotation not available")
            
            loop = asyncio.get_event_loop()
            
            if all_market:
                # 全市场快照
                data = await loop.run_in_executor(
                    None,
                    lambda: self._quotation.market_snapshot(prefix=True)
                )
            else:
                # 指定股票
                if not codes:
                    return DataResult(success=False, error="No codes specified")
                
                data = await loop.run_in_executor(
                    None,
                    lambda: self._quotation.real(codes)
                )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if data and len(data) > 0:
                # 转换为 DataFrame
                df = pd.DataFrame.from_dict(data, orient='index')
                df.reset_index(inplace=True)
                df.rename(columns={'index': 'code'}, inplace=True)
                
                # 字段标准化
                df = self._standardize_fields(df)
                
                return DataResult(
                    success=True,
                    data=df,
                    provider=self.name,
                    data_type=DataType.QUOTES,
                    latency_ms=latency_ms,
                )
            else:
                return DataResult(
                    success=False,
                    error="No data returned",
                    latency_ms=latency_ms,
                )
                
        except Exception as e:
            logger.error(f"EasyquotationProvider fetch quotes error: {e}")
            return DataResult(
                success=False,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )
    
    def _standardize_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化字段名称和值
        
        Args:
            df: 原始 DataFrame
            
        Returns:
            pd.DataFrame: 标准化后的 DataFrame
        """
        # 字段映射
        mapping = {
            'now': 'price',
            'close': 'pre_close',
            'turnover': 'raw_turnover',  # 暂存，避免混淆
            'volume': 'raw_volume',
        }
        df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
        
        # easyquotation 的 turnover 是成交量（手），volume 是成交额（元）
        if 'raw_turnover' in df.columns:
            df['volume'] = df['raw_turnover']
            df.drop('raw_turnover', axis=1, inplace=True)
        
        if 'raw_volume' in df.columns:
            df['amount'] = df['raw_volume']
            df.drop('raw_volume', axis=1, inplace=True)
        
        # 计算涨跌额和涨跌幅
        if 'price' in df.columns and 'pre_close' in df.columns:
            df['change'] = df['price'] - df['pre_close']
            df['change_pct'] = (df['change'] / df['pre_close'] * 100).fillna(0)
        
        # close 字段（盘中等于price）
        if 'price' in df.columns and 'close' not in df.columns:
            df['close'] = df['price']
        
        # 确保code是字符串
        if 'code' in df.columns:
            # 先转换为字符串，再使用str accessor
            df['code'] = df['code'].apply(lambda x: str(x).zfill(6))
        
        return df

