"""
IncrementalSimilarityEngine (增量相似度引擎)

用于替代每日从零开始的全量 DTW 矩阵计算。
核心思路：
1. 用欧式距离指纹比对检测「发生显著行为变化」的股票
2. 只对「变化股票」对相关的股票对重新用 DTW 计算
3. 从 Redis 中读取「未变化」的历史距离缓存
4. 将两者合并组装出完整的 SimilarityMatrix
"""
import logging
import time

import numpy as np

from analysis.similarity.engine import SimilarityEngine
from cache.redis_sparse_cache import RedisSparseCacheManager
from core.models.similarity_matrix import SimilarityMatrix
from utils.metrics import TickClusterMetrics

logger = logging.getLogger(__name__)

class IncrementalSimilarityEngine:
    """
    智能增量模式的相似度计算引擎。

    每日周一强制全量 (Full Rebuild)，其余交易日启用增量模式：
    - 对比当日特征向量与昨日指纹，找出"行为变异"股票
    - 仅重算涉及变异股票的股票对
    - 从 Redis 中拉取其余不变对的缓存距离
    """

    def __init__(
        self,
        baseline_engine: SimilarityEngine,
        cache_manager: RedisSparseCacheManager,
        change_threshold: float = 0.5,
        full_rebuild_weekday: int = 0,  # 0 = Monday
    ):
        """
        Args:
            baseline_engine: 底层同步/异步 DTW 引擎
            cache_manager: Redis 稀疏缓存管理器
            change_threshold: 欧式距离超过此值才视为「变化」
            full_rebuild_weekday: 每周哪天强制全量重算（0=周一）
        """
        self.engine = baseline_engine
        self.cache = cache_manager
        self.change_threshold = change_threshold
        self.full_rebuild_weekday = full_rebuild_weekday

    async def compute_similarity_incremental(
        self,
        current_date: str,
        previous_date: str,
        features_a: dict[str, np.ndarray],
        features_b: dict[str, np.ndarray],
        features_c: dict[str, np.ndarray],
        is_monday: bool = False,
        metrics: TickClusterMetrics | None = None,
    ) -> SimilarityMatrix:
        """
        增量模式执行主流程。

        Args:
            current_date: 当日日期字符串 (YYYY-MM-DD)
            previous_date: 昨日日期字符串 (YYYY-MM-DD)
            features_a/b/c: 当日特征向量字典 (code -> ndarray[240])
            is_monday: 是否强制全量
            metrics: 可选的性能追踪对象

        Returns:
            SimilarityMatrix
        """
        all_codes = list(features_a.keys())

        if metrics:
            metrics.total_stocks = len(all_codes)

        # 强制全量路径（周一 / 首次运行无缓存）
        if is_monday:
            logger.info(f"[{current_date}] 周一全量重算模式 (Full Rebuild).")
            return await self._full_rebuild(
                current_date, features_a, features_b, features_c, metrics
            )

        # 1. 读取昨日特征指纹
        yesterday_fingerprints = await self.cache.load_feature_fingerprints(
            previous_date, all_codes
        )

        # 2. 检测「变化股票」
        changed_codes = self._detect_changed_stocks(
            yesterday_fingerprints, features_a, all_codes
        )

        if metrics:
            metrics.total_changed_stocks = len(changed_codes)

        if not changed_codes:
            logger.info(f"[{current_date}] 无显著变化股票，完全复用缓存。")
            return await self._load_full_from_cache(current_date, previous_date, all_codes)

        logger.info(
            f"[{current_date}] 增量模式: {len(changed_codes)}/{len(all_codes)} 只股票需重算"
        )

        # 3. 构建需要重新计算的 (变化股票, 所有其他股票) 对集合
        pairs_to_recompute: set[tuple[str, str]] = set()
        changed_set = set(changed_codes)
        for c in changed_codes:
            for other in all_codes:
                if c != other:
                    a, b = (c, other) if c <= other else (other, c)
                    pairs_to_recompute.add((a, b))

        list(pairs_to_recompute)
        unchanged_pairs_all = [
            (s1, s2)
            for s1 in all_codes for s2 in all_codes
            if s1 < s2 and s1 not in changed_set and s2 not in changed_set
        ]

        # 4. 从 Redis 读取「不变」对的缓存距离
        time.time()
        cached_distances = await self.cache.load_sparse_matrix(
            previous_date, unchanged_pairs_all
        )
        if metrics:
            metrics.cache_hit_pairs = len(cached_distances)

        # 5. 对「变化」对重新调用底层 DTW 引擎
        t1 = time.time()
        sub_features_a = {c: features_a[c] for c in all_codes}
        sub_features_b = {c: features_b[c] for c in all_codes}
        sub_features_c = {c: features_c[c] for c in all_codes}

        new_sim_matrix = await self.engine.compute_similarity_all(
            sub_features_a, sub_features_b, sub_features_c,
            prefilter_top_k=0.05
        )

        if metrics:
            metrics.dtw_compute_time = time.time() - t1
            metrics.total_pairs_computed = len(new_sim_matrix.stock_pairs)

        # 6. 将新矩阵写入 Redis
        await self.cache.save_sparse_matrix(
            current_date,
            new_sim_matrix.stock_pairs,
            new_sim_matrix.distances
        )

        # 也将当日特征指纹保存以供明日对比
        await self.cache.save_feature_fingerprints(current_date, features_a)

        logger.info(f"[{current_date}] 增量更新完成，上传新矩阵至Redis: {len(new_sim_matrix.stock_pairs)} 对")
        return new_sim_matrix

    def _detect_changed_stocks(
        self,
        yesterday_fingerprints: dict[str, np.ndarray | None],
        today_features: dict[str, np.ndarray],
        all_codes: list[str],
    ) -> list[str]:
        """
        比对今昨特征向量的欧氏距离，返回「显著变化」的股票代码列表。
        未出现在昨日缓存中的新股票，视为「始终变化」。
        """
        changed = []

        for code in all_codes:
            yesterday = yesterday_fingerprints.get(code)
            if yesterday is None:
                # 新股票 / 昨日无数据，必须重算
                changed.append(code)
                continue

            today = today_features.get(code)
            if today is None:
                continue

            dist = float(np.linalg.norm(today - yesterday))
            if dist > self.change_threshold:
                changed.append(code)

        return changed

    async def _full_rebuild(
        self,
        date: str,
        features_a: dict[str, np.ndarray],
        features_b: dict[str, np.ndarray],
        features_c: dict[str, np.ndarray],
        metrics: TickClusterMetrics | None,
    ) -> SimilarityMatrix:
        """全量重算并将结果落盘至 Redis。"""
        t0 = time.time()
        sim = await self.engine.compute_similarity_all(
            features_a, features_b, features_c, prefilter_top_k=0.05
        )
        elapsed = time.time() - t0

        if metrics:
            metrics.dtw_compute_time = elapsed
            metrics.total_pairs_computed = len(sim.stock_pairs)

        await self.cache.save_sparse_matrix(date, sim.stock_pairs, sim.distances)
        await self.cache.save_feature_fingerprints(date, features_a)

        logger.info(f"[{date}] Full rebuild done in {elapsed:.1f}s, {len(sim.stock_pairs)} pairs.")
        return sim

    async def _load_full_from_cache(
        self, current_date: str, previous_date: str, all_codes: list[str]
    ) -> SimilarityMatrix:
        """当无任何股票变化时，从 Redis 完全复用昨日结果并打上今日戳。"""
        all_pairs = [
            (s1, s2) for s1 in all_codes for s2 in all_codes if s1 < s2
        ]
        cached = await self.cache.load_sparse_matrix(previous_date, all_pairs)

        pairs = list(cached.keys())
        distances = np.array([cached[p] for p in pairs], dtype=np.float32)

        # 也将昨日缓存转写至今日键
        await self.cache.save_sparse_matrix(current_date, pairs, distances)

        return SimilarityMatrix(stock_pairs=pairs, distances=distances)
