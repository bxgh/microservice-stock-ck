
import logging
import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Set, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor
from numba import jit
from scipy.spatial.distance import cdist

logger = logging.getLogger(__name__)

@jit(nopython=True)
def _dtw_core(series_a: np.ndarray, series_b: np.ndarray, window: int) -> float:
    """
    带 Sakoe-Chiba 窗口约束的 DTW 核心算法 (Numba 加速)
    """
    n = len(series_a)
    m = len(series_b)
    
    # 累积代价矩阵
    # 使用 inf 初始化以满足边界以外的路径不可达
    dtw_matrix = np.full((n + 1, m + 1), np.inf)
    dtw_matrix[0, 0] = 0
    
    for i in range(1, n + 1):
        # 窗口范围控制
        lower = max(1, i - window)
        upper = min(m, i + window)
        
        for j in range(lower, upper + 1):
            cost = abs(series_a[i-1] - series_b[j-1])
            # 状态转移
            dtw_matrix[i, j] = cost + min(
                dtw_matrix[i-1, j],    # 插入
                dtw_matrix[i, j-1],    # 删除
                dtw_matrix[i-1, j-1]   # 匹配
            )
            
    return dtw_matrix[n, m]

def _worker_compute_batch(
    pairs: List[Tuple[int, int]], 
    feat_a: np.ndarray, 
    feat_b: np.ndarray, 
    feat_c: np.ndarray,
    std_a: float,
    std_b: float,
    std_c: float,
    window: int,
    weights: Tuple[float, float, float]
) -> List[Tuple[int, int, float]]:
    """
    子进程计算函数
    """
    results = []
    w_a, w_b, w_c = weights
    
    for idx_i, idx_j in pairs:
        # 分别计算三个向量的 DTW
        d_a = _dtw_core(feat_a[idx_i], feat_a[idx_j], window)
        d_b = _dtw_core(feat_b[idx_i], feat_b[idx_j], window)
        d_c = _dtw_core(feat_c[idx_i], feat_c[idx_j], window)
        
        # 归一化融合
        norm_a = d_a / std_a if std_a > 0 else 0
        norm_b = d_b / std_b if std_b > 0 else 0
        norm_c = d_c / std_c if std_c > 0 else 0
        
        total_dist = w_a * norm_a + w_b * norm_b + w_c * norm_c
        results.append((idx_i, idx_j, total_dist))
        
    return results

class SimilarityEngine:
    """
    两阶段相似度计算引擎
    1. Euclidean 粗筛 (淘汰 95% 差异巨大的股票对)
    2. Numba DTW 精算 (针对剩余 5% 识别时延关联)
    """
    def __init__(self, num_workers: int = 8):
        self.num_workers = num_workers
        self.executor = ProcessPoolExecutor(max_workers=num_workers)

    async def initialize(self):
        logger.info(f"🚀 SimilarityEngine initialized with {self.num_workers} workers")

    def euclidean_prefilter(
        self, 
        feat_a: np.ndarray, 
        feat_b: np.ndarray, 
        feat_c: np.ndarray, 
        top_k_percent: float = 0.05
    ) -> List[Tuple[int, int]]:
        """
        第一阶段：Euclidean 距离粗筛
        计算量级：O(N^2 * T)
        """
        num_stocks = feat_a.shape[0]
        logger.info(f"Filtering {num_stocks} stocks (Potential pairs: {num_stocks * (num_stocks-1) // 2})")

        # 1. 对三个特征分别计算距离矩阵
        # 使用 scipy.spatial.distance.cdist 极速计算
        dist_a = cdist(feat_a, feat_a, metric='euclidean')
        dist_b = cdist(feat_b, feat_b, metric='euclidean')
        dist_c = cdist(feat_c, feat_c, metric='euclidean')

        # 2. 这里的融合不考虑时间错位，仅作为粗筛
        # 权重与 DTW 保持一致: 0.5, 0.3, 0.2
        combined_dist = 0.5 * dist_a + 0.3 * dist_b + 0.2 * dist_c

        # 3. 提取上三角索引（避免重复对）
        triu_indices = np.triu_indices(num_stocks, k=1)
        flat_distances = combined_dist[triu_indices]

        # 4. 计算分位数阈值
        threshold = np.percentile(flat_distances, top_k_percent * 100)
        
        # 5. 过滤出候选对
        mask = flat_distances <= threshold
        idx_i = triu_indices[0][mask]
        idx_j = triu_indices[1][mask]
        
        candidates = list(zip(idx_i, idx_j))
        logger.info(f"✅ Euclidean filtering done. Kept {len(candidates)} pairs (Threshold: {threshold:.4f})")
        
        return candidates

    async def compute_dtw_parallel(
        self,
        candidates: List[Tuple[int, int]],
        feat_a: np.ndarray,
        feat_b: np.ndarray,
        feat_c: np.ndarray,
        window: int = 15,
        weights: Tuple[float, float, float] = (0.5, 0.3, 0.2)
    ) -> Dict[Tuple[int, int], float]:
        """
        第二阶段：并行计算 DTW
        """
        if not candidates:
            return {}

        # 计算全局标准差用于归一化
        std_a = np.std(feat_a)
        std_b = np.std(feat_b)
        std_c = np.std(feat_c)

        # 任务分片
        chunk_size = max(1, len(candidates) // (self.num_workers * 4))
        chunks = [candidates[i:i + chunk_size] for i in range(0, len(candidates), chunk_size)]
        
        logger.info(f"Dispatching {len(candidates)} pairs to {len(chunks)} tasks...")

        loop = asyncio.get_running_loop()
        tasks = []
        for chunk in chunks:
            tasks.append(loop.run_in_executor(
                self.executor,
                _worker_compute_batch,
                chunk, feat_a, feat_b, feat_c,
                std_a, std_b, std_c,
                window, weights
            ))

        # 等待所有子任务完成
        results = await asyncio.gather(*tasks)
        
        # 汇总结果
        final_results = {}
        for chunk_res in results:
            for i, j, dist in chunk_res:
                final_results[(i, j)] = dist

        logger.info(f"✅ DTW calculations completed for {len(final_results)} pairs")
        return final_results

    async def close(self):
        self.executor.shutdown()
        logger.info("SimilarityEngine closed")

