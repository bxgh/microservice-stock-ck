import logging

import numpy as np

logger = logging.getLogger(__name__)

def compute_tlcc(
    series_a: np.ndarray,
    series_b: np.ndarray,
    max_lag: int = 15
) -> tuple[int, float]:
    """
    计算两段时间序列的“时滞互相关” (Time-Lagged Cross Correlation)。
    用于确定存在共振关系的两只股票在时间轴上的先后因果。

    Args:
        series_a: 第一只股票的收益率时序数据数组 (Numpy array)
        series_b: 第二只股票的收益率时序数据数组 (Numpy array)
        max_lag: 允许搜索的最大向前/向后果延迟步长（比如以分钟为单位的 15 步）

    Returns:
        best_lag (int): 达到最大相关系数时的步数。正数代表 A 领先 B；负数表示 B 领先 A。
        max_corr (float): 该步数下的最大皮尔逊相关系数
    """
    n = len(series_a)
    m = len(series_b)

    # 防止传入过小的数据截断
    if n < max_lag * 2 or m < max_lag * 2 or n != m:
        logger.warning(f"Time series length ({n},{m}) is invalid for lag ({max_lag}) calculation.")
        return 0, 0.0

    lags = range(-max_lag, max_lag + 1)
    correlations = []

    # 当 std 为 0 时的除零保护，在底层 np.corrcoef 会返回 nan
    # 我们希望出现 nan 时用 0.0 代替
    for lag in lags:
        if lag > 0:
            # lag > 0, 意味着 A 向前移动了 lag 的位置去跟 B 的后部分对比，暗示 A 发生在前，领先 B
            corr = np.corrcoef(series_a[:-lag], series_b[lag:])[0, 1]
        elif lag < 0:
            # lag < 0, 意味着 B 向前漂移也就是 B 比较早发生，B 领先 A
            corr = np.corrcoef(series_a[-lag:], series_b[:lag])[0, 1]
        else:
            corr = np.corrcoef(series_a, series_b)[0, 1]

        # 捕捉常数发散，如一字涨停或者完全停牌的无波动股票导致的 np.nan
        if np.isnan(corr):
            corr = 0.0

        correlations.append(corr)

    # 找到所有相关系数中绝对值最大的
    max_idx = int(np.argmax(correlations))
    best_lag = lags[max_idx]
    max_corr = float(correlations[max_idx])

    return best_lag, max_corr
