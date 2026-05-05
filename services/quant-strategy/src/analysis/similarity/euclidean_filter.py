import numpy as np
from scipy.spatial.distance import pdist


def euclidean_prefilter(
    features_a: dict[str, np.ndarray],
    features_b: dict[str, np.ndarray],
    features_c: dict[str, np.ndarray],
    top_k_percent: float = 0.05,
    weights: tuple[float, float, float] = (0.5, 0.3, 0.2)
) -> set[tuple[str, str]]:
    """
    第一阶段：Euclidean距离预筛选

    快速剔除明显不相关的股票对，使用欧式距离将候选池缩小到 top_k_percent (如前5%)，
    随后再交给DTW进行精算。

    Args:
        features_a: 向量A（如主动买入强度）的特征映射 {stock_code: [240维数组]}
        features_b: 向量B（如盘口失衡）的特征映射
        features_c: 向量C（如收益率）的特征映射
        top_k_percent: 保留距离最小的前X%股票对进入下一阶段
        weights: 三个特征向量在粗筛阶段的权重 (A, B, C)

    Returns:
        符合条件的候选股票对集合 Set[(stock_1, stock_2)] (保证 stock_1 < stock_2)
    """
    stocks = sorted(features_a.keys())
    n_stocks = len(stocks)

    if n_stocks < 2:
        return set()

    # 构建N x 240的特征矩阵
    # 为了防止某些股票由于数据缺失而未包含在所有三个特征字典中，默认使用0向量填充
    # 但实际应用中应该由前置的数据清洗模块保证一致性
    dim = len(next(iter(features_a.values()))) if features_a else 240

    mat_a = np.zeros((n_stocks, dim))
    mat_b = np.zeros((n_stocks, dim))
    mat_c = np.zeros((n_stocks, dim))

    for i, code in enumerate(stocks):
        mat_a[i] = features_a.get(code, np.zeros(dim))
        mat_b[i] = features_b.get(code, np.zeros(dim))
        mat_c[i] = features_c.get(code, np.zeros(dim))

    # 使用scipy的pdist计算成对距离，返回一维的压缩距离数组
    # pdist效率比双重循环高几个数量级，由底层C实现
    dist_a = pdist(mat_a, metric='euclidean')
    dist_b = pdist(mat_b, metric='euclidean')
    dist_c = pdist(mat_c, metric='euclidean')

    # 防止标准差为0导致的除零异常
    std_a = np.std(dist_a) if len(dist_a) > 0 and np.std(dist_a) > 0 else 1.0
    std_b = np.std(dist_b) if len(dist_b) > 0 and np.std(dist_b) > 0 else 1.0
    std_c = np.std(dist_c) if len(dist_c) > 0 and np.std(dist_c) > 0 else 1.0

    # 特征距离归一化与加权
    norm_dist_a = dist_a / std_a
    norm_dist_b = dist_b / std_b
    norm_dist_c = dist_c / std_c

    final_dist = (weights[0] * norm_dist_a) + (weights[1] * norm_dist_b) + (weights[2] * norm_dist_c)

    # 确定阈值
    k_index = int(len(final_dist) * top_k_percent)
    if k_index == 0:
        k_index = 1

    # 获取属于前k_percent范围内的过滤阈值
    # 使用 partition 可实现 O(N) 获取前K个值
    threshold = np.partition(final_dist, k_index)[k_index]

    # 获取距离小于等于阈值的索引
    valid_indices = np.where(final_dist <= threshold)[0]

    # 将压缩的一维索引还原为二维的组合 (i, j) 对应的股票代码
    # scipy.spatial.distance 的组合顺序机制：
    # 0 vs 1, 0 vs 2, ..., 0 vs n-1
    # 1 vs 2, 1 vs 3, ..., 1 vs n-1
    # ...
    # n-2 vs n-1

    # 为了利用 numpy 向量化提速获取索引，可临时构造方阵的上三角的索引映射
    # 生成方式有很多，此处基于 np.triu_indices 映射
    row_idx, col_idx = np.triu_indices(n_stocks, k=1)

    candidates = set()
    for idx in valid_indices:
        # Pdist生成的是上三角矩阵展平后的1D数组
        r = row_idx[idx]
        c = col_idx[idx]

        stock_1 = stocks[r]
        stock_2 = stocks[c]

        # 始终保持有序 (小的在前) 以防死锁或去重
        if stock_1 < stock_2:
            candidates.add((stock_1, stock_2))
        else:
            candidates.add((stock_2, stock_1))

    return candidates
