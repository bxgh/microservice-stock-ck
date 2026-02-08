from decimal import Decimal
import pandas as pd
from .models import MultiplesMetrics
from .interfaces import IAnalyzer

class MultiplesAnalyzer(IAnalyzer):
    """发行价倍数分析器"""
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> MultiplesMetrics:
        """
        计算相对于发行价的倍数指标
        
        Args:
            df: 包含 K 线数据的 DataFrame
            kwargs: 必须包含 'issue_price' (Decimal)
        """
        issue_price = kwargs.get('issue_price')
        if isinstance(issue_price, (str, float, int)):
            issue_price = Decimal(str(issue_price))
            
        if not df.empty:
            # 1. 首波涨幅 (相对于首日开盘价)
            # 首日开盘价
            first_open = float(df.iloc[0]['open'])
            # 找到首波峰值 (同 DrawdownAnalyzer 逻辑，前 120 天)
            df_peak_search = df.iloc[:120]
            first_wave_high = float(df_peak_search['high'].max())
            first_wave_gain = (first_wave_high - first_open) / first_open
            
            # 2. 最高/发行价倍数
            hist_high = float(df['high'].max())
            current_price = float(df.iloc[-1]['close'])
            
            high_to_issue = 0.0
            current_to_issue = 0.0
            
            if issue_price and issue_price > 0:
                high_to_issue = hist_high / float(issue_price)
                current_to_issue = current_price / float(issue_price)
                
            return MultiplesMetrics(
                first_wave_gain=float(first_wave_gain),
                high_to_issue=float(high_to_issue),
                current_to_issue=float(current_to_issue),
                issue_price=issue_price
            )
            
        return MultiplesMetrics(0.0, 0.0, 0.0, issue_price)
