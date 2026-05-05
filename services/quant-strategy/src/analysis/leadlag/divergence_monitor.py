import logging
from enum import Enum

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class TrendPhase(Enum):
    FORMATION = "合力形成期"
    STEADY = "稳定运行期"
    DISSOLUTION = "瓦解期"

def compute_divergence(
    cluster_stocks: list[str],
    returns: dict[str, np.ndarray],
    window: int = 30
) -> np.ndarray:
    """
    计算给定股票聚集内的运行时分歧度。
    分歧度定义为同一时刻群内所有股票横截面收益率的标准差。
    通过 Pandas 滚动计算 (rolling) 平滑波动。

    Args:
        cluster_stocks: 群内的股票代码集合
        returns: 全局收益率字典映射 {stock_code: returns_array}
        window: 滚动窗口长度（如 30 分钟）

    Returns:
        np.ndarray: 平滑后的分歧度一维数组序列，长度同输入序列
    """
    # 提取需要的收益率序列，并忽略缺失序列
    valid_returns = []
    for s in cluster_stocks:
        if s in returns:
            valid_returns.append(returns[s])

    if not valid_returns:
        logger.warning("No valid return series found to compute divergence.")
        return np.array([])

    arr = np.array(valid_returns)
    # 计算横截面（axis=0 因为行为股票编号，列为时间步长）的标准差
    # 为了防止全 0 或只有1只股票的计算出异，直接通过 pd DataFrame 处理
    df = pd.DataFrame(arr.T)

    # 每时刻截面标准差
    cross_sectional_std = df.std(axis=1)

    # 滚动平滑，min_periods=1 保证初期也有数据，而不会全部是 NaN
    rolling_std = cross_sectional_std.rolling(window=window, min_periods=1).mean()

    return rolling_std.values


def classify_trend_phase(
    current_divergence: float,
    history_divergence: np.ndarray,
    p_low: float = 20.0,
    p_high: float = 80.0
) -> TrendPhase:
    """
    根据历史分歧度分布推断目前阶段。

    - 如果当前分歧度 < 历史 20% 分位数，说明大家走的极为一致，趋势正在形成 (FORMATION)
    - 如果当前分歧度 > 历史 80% 分位数，说明大家走势背离，发生内部分歧，趋势瓦解 (DISSOLUTION)
    - 居中表示稳定运行 (STEADY)

    Args:
        current_divergence: 当前最末截面的近期分歧度
        history_divergence: 过去一段时间产生的分歧度历史序列
    """
    if len(history_divergence) == 0:
        return TrendPhase.STEADY

    # 排除开盘期间等可能的 nan 值
    valid_history = history_divergence[~np.isnan(history_divergence)]
    if len(valid_history) == 0:
        return TrendPhase.STEADY

    p20 = np.percentile(valid_history, p_low)
    p80 = np.percentile(valid_history, p_high)

    # 为防止 p20 == p80 (如直线无波动情况)
    if p20 == p80:
        return TrendPhase.STEADY

    if current_divergence < p20:
        return TrendPhase.FORMATION
    elif current_divergence > p80:
        return TrendPhase.DISSOLUTION
    else:
        return TrendPhase.STEADY
