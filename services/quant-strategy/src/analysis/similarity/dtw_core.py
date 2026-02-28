import numpy as np
from numba import njit  # type: ignore


@njit(fastmath=True)  # type: ignore
def dtw_distance_with_window(
    series_a: np.ndarray,
    series_b: np.ndarray,
    window: int = 15
) -> float:
    """
    带 Sakoe-Chiba 窗口约束的 DTW 动态规划核心算法 (Numba加速版本)。

    使用 JIT 编译为机器码，性能接近纯C。
    使用 Sakoe-Chiba 窗口约束将复杂度从 O(N^2) 降至 O(N * W)。

    Args:
        series_a: 第一只股票的序列 (例如 240 维)
        series_b: 第二只股票的序列 (例如 240 维)
        window: 最大允许的时间扭曲步数 (默认 15)

    Returns:
        float: 最终的最小累积归一化距离
    """
    n = len(series_a)
    m = len(series_b)

    # 初始化累积距离矩阵（使用 np.inf 填充）
    dtw_matrix = np.full((n + 1, m + 1), fill_value=np.inf, dtype=np.float64)
    dtw_matrix[0, 0] = 0.0

    # 调整窗口大小
    w = max(window, abs(n - m))

    for i in range(1, n + 1):
        # Sakoe-Chiba 带宽范围限制
        # j 的范围必须在 [max(1, i - w), min(m, i + w)]
        start_j = max(1, i - w)
        end_j = min(m, i + w)

        for j in range(start_j, end_j + 1):

            # 使用欧氏距离作为点对点的成本
            # Note: numpy在njit内对标量操作极其快
            # 计算绝对误差
            cost = abs(series_a[i - 1] - series_b[j - 1])

            # DP 递推式： cost + 最小邻居成本
            min_prev = min(
                dtw_matrix[i - 1, j],      # 插入 (Insertion)
                dtw_matrix[i, j - 1],      # 删除 (Deletion)
                dtw_matrix[i - 1, j - 1]   # 匹配 (Match)
            )

            dtw_matrix[i, j] = cost + min_prev

    # 计算均一化距离（避免长序列优势）
    # (n + m)是可能走过的最大路径长度
    final_distance = dtw_matrix[n, m] / (n + m)

    return float(final_distance)
