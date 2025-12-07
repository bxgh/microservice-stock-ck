# -*- coding: utf-8 -*-
"""
EPIC-007 Baostock 数据提供者

基于 baostock 库实现的数据提供者,支持:
- 历史K线 (HISTORY) - 1990年至今

⚠️ 注意: baostock 需要通过 proxychains4 运行!

@author: EPIC-007
@date: 2025-12-06
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import DataProvider, DataResult, DataType

logger = logging.getLogger(__name__)


class BaostockProvider(DataProvider):
    """Baostock 数据提供者
    
    使用 baostock 获取历史K线数据。
    
    优势:
    - 完整历史数据 (1990年至今)
    - 官方清洗,数据质量高
    - 完全免费
    
    ⚠️ 重要: 
    需要通过 proxychains4 运行!
    ```bash
    proxychains4 python your_script.py
    ```
    """
    
    def __init__(
        self,
        priority: Optional[Dict[DataType, int]] = None,
    ):
        """初始化
        
        Args:
            priority: 自定义优先级
        """
        self._bs = None
        self._logged_in = False
        self._lock = asyncio.Lock()
        
        # 默认优先级 (作为备选)
        self._priority = priority or {
            DataType.HISTORY: 2,  # K线备选
        }
    
    @property
    def name(self) -> str:
        return "baostock"
    
    @property
    def capabilities(self) -> List[DataType]:
        return [DataType.HISTORY]
    
    @property
    def priority_map(self) -> Dict[DataType, int]:
        return self._priority
    
    @property
    def requires_proxy(self) -> bool:
        """baostock 需要 proxychains4"""
        return True
    
    async def initialize(self) -> bool:
        """初始化并登录"""
        try:
            import baostock as bs
            self._bs = bs
            
            loop = asyncio.get_event_loop()
            lg = await loop.run_in_executor(
                None,
                bs.login
            )
            
            if lg.error_code == '0':
                self._logged_in = True
                logger.info("BaostockProvider initialized and logged in")
                return True
            else:
                logger.error(f"BaostockProvider login failed: {lg.error_code} - {lg.error_msg}")
                logger.warning("⚠️  baostock 需要通过 proxychains4 运行!")
                return False
                
        except Exception as e:
            logger.error(f"BaostockProvider initialization error: {e}")
            logger.warning("⚠️  baostock 需要通过 proxychains4 运行!")
            return False
    
    async def close(self) -> None:
        """登出并关闭"""
        if self._logged_in and self._bs:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._bs.logout)
            except Exception as e:
                logger.warning(f"BaostockProvider logout error: {e}")
        
        self._bs = None
        self._logged_in = False
        logger.info("BaostockProvider closed")
    
    async def health_check(self) -> bool:
        """健康检查"""
        if not self._logged_in or self._bs is None:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            rs = await loop.run_in_executor(
                None,
                lambda: self._bs.query_history_k_data_plus(
                    "sh.600519", "date,close",
                    start_date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                    end_date=datetime.now().strftime("%Y-%m-%d"),
                    frequency="d"
                )
            )
            return rs.error_code == '0'
        except Exception as e:
            logger.warning(f"BaostockProvider health check failed: {e}")
            return False
    
    async def fetch(self, data_type: DataType, **kwargs) -> DataResult:
        """获取数据"""
        if data_type == DataType.HISTORY:
            return await self._fetch_history(**kwargs)
        else:
            return DataResult(
                success=False,
                error=f"Unsupported data type: {data_type.value}"
            )
    
    async def _ensure_login(self) -> bool:
        """确保已登录"""
        async with self._lock:
            if not self._logged_in:
                return await self.initialize()
            return True
    
    def _convert_code(self, code: str) -> str:
        """转换股票代码格式
        
        baostock 需要 sh./sz. 前缀
        """
        if code.startswith(("sh.", "sz.")):
            return code
        
        if code.startswith("6"):
            return f"sh.{code}"
        else:
            return f"sz.{code}"
    
    async def _fetch_history(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = "d",
        fields: str = "date,open,high,low,close,volume,amount,pctChg",
        adjustflag: str = "3",  # 默认不复权: 1=后复权, 2=前复权, 3=不复权
        **kwargs
    ) -> DataResult:
        """获取历史K线数据
        
        Args:
            code: 股票代码 (如 "600519" 或 "sh.600519")
            start_date: 开始日期 (YYYY-MM-DD), 默认90天前
            end_date: 结束日期 (YYYY-MM-DD), 默认今天
            frequency: 周期 ("d"=日, "w"=周, "m"=月, "5"=5分钟, ...)
            fields: 返回字段
            adjustflag: 复权类型 (1=后复权, 2=前复权, 3=不复权)
        
        Returns:
            DataFrame 包含 OHLCV 等数据
        """
        start_time = time.time()
        
        try:
            if not await self._ensure_login():
                return DataResult(
                    success=False, 
                    error="Not logged in. ⚠️ baostock 需要通过 proxychains4 运行!"
                )
            
            # 转换代码格式
            bs_code = self._convert_code(code)
            
            # 默认日期
            end = end_date or datetime.now().strftime("%Y-%m-%d")
            start = start_date or (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            
            loop = asyncio.get_event_loop()
            rs = await loop.run_in_executor(
                None,
                lambda: self._bs.query_history_k_data_plus(
                    bs_code, fields,
                    start_date=start, end_date=end,
                    frequency=frequency,
                    adjustflag=adjustflag,  # 复权参数
                )
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if rs.error_code != '0':
                return DataResult(
                    success=False,
                    error=f"Query error: {rs.error_code} - {rs.error_msg}",
                    latency_ms=latency_ms,
                )
            
            # 读取数据
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if len(data_list) > 0:
                df = pd.DataFrame(data_list, columns=rs.fields)
                return DataResult(
                    success=True,
                    data=df,
                    latency_ms=latency_ms,
                    extra={
                        "code": bs_code,
                        "start_date": start,
                        "end_date": end,
                        "frequency": frequency,
                    },
                )
            else:
                return DataResult(
                    success=False,
                    error=f"No history data for {bs_code}",
                    latency_ms=latency_ms,
                )
                
        except Exception as e:
            logger.error(f"BaostockProvider fetch history error: {e}")
            return DataResult(
                success=False,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )
