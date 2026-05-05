import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

from sqlalchemy import tuple_

logger = logging.getLogger(__name__)

class EcoSignalStrategy:
    """
    生态信号计算引擎 (EPIC-017 Story 17.5)
    
    读取不同 label 下的 GitHub 活跃度数据，计算复合特征，
    应用 Z-Score 生成生态热度信号。
    """
    
    def __init__(self):
        # 权重设置
        self.w_momentum = 0.5
        self.w_responsiveness = 0.2
        self.w_growth = 0.3
        
        # 信号级别阈值
        self.threshold_warm = 1.0
        self.threshold_hot = 1.5
        self.threshold_extreme = 2.0

    def generate_signals(self, raw_df: pd.DataFrame, target_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        基于原始收集到的 `github_repo_metrics` 聚合生成当期的 Z-Score。
        
        Args:
            raw_df: 由 AltDataDAO.get_raw_metrics 获取的时间序列数据。包含所有的历史快照。
            target_date: 执行信号计算的基础时间。
            
        Returns:
            DataFrame 包含将要插入 ecosystem_signals 表的内容。
        """
        if raw_df is None or raw_df.empty:
            logger.warning("No raw data provided to generate signals.")
            return pd.DataFrame()
            
        if target_date is None:
            target_date = datetime.now()
            
        # 提取当前 label (传入的 df 应该是按单个 label 获取的，校验取第一条)
        label = raw_df['label'].iloc[0]
        
        # 1. 把所有 repo 聚合成按天 (date) 或者按采集批次的时间序列
        # 注意: 因为数据存在一天多次采集，我们这里以 'collect_time' 按天/批次做维度合并
        
        # 为了统一定期信号生成，我们按日期截断进行 groupBy，每日求所有 repo 的总和/均值
        raw_df['date'] = raw_df['collect_time'].dt.date
        
        # 异常数据处理: 避免全是 NaN 导致报错
        raw_df.fillna(0, inplace=True)
        
        agg_df = raw_df.groupby('date').agg({
            'pr_merged_acceleration': 'sum',
            'issue_close_median_hours': lambda x: x[x > 0].mean() if len(x[x > 0]) > 0 else 0,
            'star_delta_7d': 'sum',
            'contributor_count_30d': 'sum'
        }).reset_index()
        
        # 2. 计算复合特征
        agg_df['eco_momentum'] = agg_df['pr_merged_acceleration']
        
        # responsiveness: 取倒数。防止除 0
        max_valid_hours = 24 * 365 # 强制极值(假设一年没人回)
        agg_df['eco_responsiveness'] = agg_df['issue_close_median_hours'].apply(
            lambda h: 1 / h if h > 0 else 1 / max_valid_hours
        )
        # 将倒数规范化，将其放大到一个便于观察的数量级 (例如 1 -> 1/1 = 1, 10 -> 1/10 = 0.1)
        # 这里仅体现相对相对大小即可
        
        agg_df['eco_growth'] = agg_df['star_delta_7d'] + agg_df['contributor_count_30d']
        
        # 3. 计算 Z-Score (使用滚动窗口或全局均值(样本不足时))
        # 真实环境中这里会累计至少 30+ 天的数据
        # 这里处理样本不足的情况：使用全量样本并增加微小扰动 epsilon 以免标准差为 0
        epsilon = 1e-6
        
        def z_score(series):
            if len(series) <= 1 or series.std() < epsilon:
                return pd.Series(np.zeros(len(series)))
            return (series - series.mean()) / series.std()

        agg_df['z_momentum'] = z_score(agg_df['eco_momentum'])
        agg_df['z_responsiveness'] = z_score(agg_df['eco_responsiveness'])
        agg_df['z_growth'] = z_score(agg_df['eco_growth'])
        
        # 4. 综合 Z-Score
        agg_df['composite_z_score'] = (
            self.w_momentum * agg_df['z_momentum'] +
            self.w_responsiveness * agg_df['z_responsiveness'] +
            self.w_growth * agg_df['z_growth']
        )
        
        # 5. 生成最后一条记录的 Signal
        # 我们只对外暴露基于当下（最近日期）产生的唯一一条最新信号进行落盘
        latest_record = agg_df.sort_values('date', ascending=False).iloc[0]
        
        z_val = latest_record['composite_z_score']
        
        if z_val >= self.threshold_extreme:
            signal_level = "EXTREME"
        elif z_val >= self.threshold_hot:
            signal_level = "HOT"
        elif z_val >= self.threshold_warm:
            signal_level = "WARM"
        else:
            signal_level = "NEUTRAL"
            
        # 寻找主导因子
        z_components = {
            "eco_momentum": latest_record['z_momentum'],
            "eco_responsiveness": latest_record['z_responsiveness'],
            "eco_growth": latest_record['z_growth']
        }
        dominant_factor = max(z_components, key=z_components.get)
        
        # 构建 Detail JSON
        detail_dict = {
            "z_momentum": round(latest_record['z_momentum'], 4),
            "z_responsiveness": round(latest_record['z_responsiveness'], 4),
            "z_growth": round(latest_record['z_growth'], 4),
            "raw_momentum": int(latest_record['eco_momentum']),
            "raw_growth": int(latest_record['eco_growth'])
        }
        
        # 考虑到 pandas 写入 ClickHouse，组装 DataFrame
        import json
        result_df = pd.DataFrame([{
            "signal_time": target_date,
            "label": label,
            "composite_z_score": float(z_val),
            "dominant_factor": dominant_factor,
            "signal_level": signal_level,
            "detail": json.dumps(detail_dict)
        }])
        
        return result_df
