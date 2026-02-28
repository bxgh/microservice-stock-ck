import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from src.core.models.similarity_matrix import SimilarityMatrix
from .dtw_core import dtw_distance_with_window
from .euclidean_filter import euclidean_prefilter

logger = logging.getLogger(__name__)

# 全局共享的只读数据，供给 ProcessPool 使用以减少进程间通信开销
# 在生产环境下，可通过共享内存或提前初始化降低传参成本
_PROCESS_SHARED_FEATURES_A: dict[str, np.ndarray] = {}
_PROCESS_SHARED_FEATURES_B: dict[str, np.ndarray] = {}
_PROCESS_SHARED_FEATURES_C: dict[str, np.ndarray] = {}

def _init_worker(
    features_a: dict[str, np.ndarray],
    features_b: dict[str, np.ndarray],
    features_c: dict[str, np.ndarray]
) -> None:
    """初始化进程池 worker 环境，将共享数据挂载到进程全局"""
    global _PROCESS_SHARED_FEATURES_A, _PROCESS_SHARED_FEATURES_B, _PROCESS_SHARED_FEATURES_C
    _PROCESS_SHARED_FEATURES_A = features_a
    _PROCESS_SHARED_FEATURES_B = features_b
    _PROCESS_SHARED_FEATURES_C = features_c


def _process_dtw_chunk(
    pairs_chunk: list[tuple[str, str]],
    dtw_window: int = 15,
    weights: tuple[float, float, float] = (0.5, 0.3, 0.2)
) -> list[tuple[str, str, float, float, float]]:
    """
    进程执行器：在独立进程中串行执行 DTW 计算
    Return:
        List of (stock_1, stock_2, final_distance)
    """
    global _PROCESS_SHARED_FEATURES_A, _PROCESS_SHARED_FEATURES_B, _PROCESS_SHARED_FEATURES_C

    results = []
    # 如果该进程缺少某些特征，提供全是 0 的默认值避免计算崩溃
    dim = len(next(iter(_PROCESS_SHARED_FEATURES_A.values()))) if _PROCESS_SHARED_FEATURES_A else 240
    default_vec = np.zeros(dim)

    for (s1, s2) in pairs_chunk:
        # 1. 提取 A, B, C 特征序列
        a1 = _PROCESS_SHARED_FEATURES_A.get(s1, default_vec)
        a2 = _PROCESS_SHARED_FEATURES_A.get(s2, default_vec)

        b1 = _PROCESS_SHARED_FEATURES_B.get(s1, default_vec)
        b2 = _PROCESS_SHARED_FEATURES_B.get(s2, default_vec)

        c1 = _PROCESS_SHARED_FEATURES_C.get(s1, default_vec)
        c2 = _PROCESS_SHARED_FEATURES_C.get(s2, default_vec)

        # 2. 单独调用 numba JIT 函数计算 DTW距离
        # 只要有一处抛出异常，会导致该股票对计算降级
        try:
            dist_a = dtw_distance_with_window(a1, a2, window=dtw_window)
            dist_b = dtw_distance_with_window(b1, b2, window=dtw_window)
            dist_c = dtw_distance_with_window(c1, c2, window=dtw_window)

            results.append((s1, s2, dist_a, dist_b, dist_c))
        except Exception as e:
            # 万一计算错误（如输入序列含 NaN 等），记录高距离表示不相关
            logger.error(f"DTW calculation failed for {s1} - {s2}: {e}")
            results.append((s1, s2, np.inf, np.inf, np.inf))

    return results


class SimilarityEngine:
    """两阶段相似度计算引擎"""

    def __init__(self, max_workers: int = 8, dtw_window: int = 15):
        """
        Args:
            max_workers: 进程池大小，默认建议使用 CPU 核心数 - 2
            dtw_window: Sakoe-Chiba 动态时间扭曲窗口长度，默认 15
        """
        self.max_workers = max_workers
        self.dtw_window = dtw_window

    async def compute_similarity_all(
        self,
        features_a: dict[str, np.ndarray],
        features_b: dict[str, np.ndarray],
        features_c: dict[str, np.ndarray],
        weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
        prefilter_top_k: float = 0.05
    ) -> SimilarityMatrix:
        """
        执行两阶段计算流程并返回完整矩阵。
        """
        logger.info(f"Phase 1: Euclidean pre-filtering start (top {prefilter_top_k*100}%)")
        candidates_set: set[tuple[str, str]] = euclidean_prefilter(
            features_a, features_b, features_c,
            top_k_percent=prefilter_top_k,
            weights=weights
        )
        candidates = list(candidates_set)
        total_candidates = len(candidates)
        logger.info(f"Phase 1 finished. Kept {total_candidates} candidate pairs for DTW.")

        if total_candidates == 0:
            return SimilarityMatrix(stock_pairs=[], distances=np.array([]))

        # 根据候选数与进程数，将列表等分 chunk
        # 控制合适的 Chunk 大小有利 CPU cache 命中
        chunk_size = max(1000, total_candidates // (self.max_workers * 4))
        chunks = [candidates[i:i + chunk_size] for i in range(0, total_candidates, chunk_size)]
        logger.info(f"Phase 2: Dispatching {len(chunks)} chunks across {self.max_workers} processes.")

        loop = asyncio.get_running_loop()

        # 阶段二: 多进程计算 DTW
        all_raw_results: list[tuple[str, str, float, float, float]] = []

        with ProcessPoolExecutor(
            max_workers=self.max_workers,
            initializer=_init_worker,
            initargs=(features_a, features_b, features_c)
        ) as pool:

            # 使用 asyncio.gather 和 run_in_executor 聚合协程结果
            tasks = [
                loop.run_in_executor(
                    pool,
                    _process_dtw_chunk,
                    chunk,
                    self.dtw_window,
                    weights
                )
                for chunk in chunks
            ]

            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

            for index, res in enumerate(chunk_results):
                if isinstance(res, BaseException):
                    logger.error(f"Chunk {index} failed with ProcessPool exception: {res}")
                else:
                    all_raw_results.extend(res)

        logger.info(f"Phase 2 finished computed pairs: {len(all_raw_results)}")

        # 阶段三: 根据特征归一化标准差进行整合
        # 搜集所有距离算出均值方差以归一化
        valid_a = [r[2] for r in all_raw_results if not np.isinf(r[2])]
        valid_b = [r[3] for r in all_raw_results if not np.isinf(r[3])]
        valid_c = [r[4] for r in all_raw_results if not np.isinf(r[4])]

        std_a = np.std(valid_a) if len(valid_a) > 0 and np.std(valid_a) > 0 else 1.0
        std_b = np.std(valid_b) if len(valid_b) > 0 and np.std(valid_b) > 0 else 1.0
        std_c = np.std(valid_c) if len(valid_c) > 0 and np.std(valid_c) > 0 else 1.0

        final_pairs = []
        final_distances = []

        for r in all_raw_results:
            s1, s2, d_a, d_b, d_c = r
            if np.isinf(d_a):
                continue

            norm_a = d_a / std_a
            norm_b = d_b / std_b
            norm_c = d_c / std_c

            f_dist = (weights[0] * norm_a) + (weights[1] * norm_b) + (weights[2] * norm_c)
            final_pairs.append((s1, s2))
            final_distances.append(f_dist)

        logger.info("Phase 3: Final normalized distances computed.")

        return SimilarityMatrix(
            stock_pairs=final_pairs,
            distances=np.array(final_distances, dtype=np.float32)
        )
