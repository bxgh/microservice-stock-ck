from typing import Protocol, Any
import pandas as pd

class IAnalyzer(Protocol):
    """分析器通用接口协议"""
    def analyze(self, df: pd.DataFrame, **kwargs: Any) -> Any:
        """
        执行量化计算分析
        
        Args:
            df: 包含 K 线数据的 DataFrame (应包含 high, low, close, volume, turnover 等列)
            **kwargs: 其他必要的参数 (如 issue_price, benchmark_df 等)
            
        Returns:
            返回对应的 Metrics 数据对象
        """
        ...
