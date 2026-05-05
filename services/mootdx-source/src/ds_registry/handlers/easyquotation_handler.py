"""
EasyQuotation Handler
新浪/腾讯行情数据源处理器

职责:
- 管理 easyquotation 客户端的生命周期
- 提供实时行情数据获取接口（作为 mootdx 的降级备选）
- 异步包装同步调用
"""
import asyncio
import logging
from typing import List, Dict, Any
import pandas as pd
import easyquotation

logger = logging.getLogger("easyquotation-handler")


class EasyquotationHandler:
    """
    新浪/腾讯行情（easyquotation）数据源处理器
    
    封装 easyquotation 库的调用逻辑，主要用于实时行情的降级场景。
    """
    
    def __init__(self):
        self.client = None
    
    async def initialize(self) -> None:
        """
        初始化 easyquotation 客户端
        
        使用新浪行情源（sina）
        """
        loop = asyncio.get_event_loop()
        try:
            self.client = await loop.run_in_executor(
                None,
                lambda: easyquotation.use('sina')
            )
            logger.info("✓ Easyquotation client initialized (sina)")
        except Exception as e:
            logger.error(f"Failed to initialize easyquotation: {e}")
            self.client = None
    
    async def close(self) -> None:
        """
        关闭 easyquotation 客户端
        
        注意: easyquotation 客户端通常不需要显式关闭，此方法仅用于统一接口
        """
        if self.client:
            self.client = None
            logger.info("Easyquotation client closed")
    
    async def get_quotes(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        获取实时行情
        
        Args:
            codes: 股票代码列表
            params: 额外参数（暂未使用）
        
        Returns:
            DataFrame 包含字段:
            - code: 股票代码
            - name: 股票名称
            - open, close, now: 开盘/收盘/现价
            - high, low: 最高/最低
            - buy, sell: 买一/卖一
            - volume, amount: 成交量/额
            - bid1-5, ask1-5: 五档买卖
            - date, time: 日期时间
        
        Note:
            - 直接调用新浪/腾讯 HTTP 接口
            - 需要外网访问或代理
            - 有频率限制（约60次/分钟）
        """
        if not self.client:
            logger.warning("Easyquotation client not initialized")
            return pd.DataFrame()
        
        if not codes:
            return pd.DataFrame()
        
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(
                None,
                lambda: self.client.stocks(codes)
            )
            
            if data:
                # 转换为 DataFrame 格式
                # easyquotation 返回 dict[code, dict]，需转置
                df = pd.DataFrame(data).T.reset_index()
                df.rename(columns={"index": "code"}, inplace=True)
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"Easyquotation get_quotes failed: {e}")
            return pd.DataFrame()
