"""
Redis Sparse Matrix Cache

负责将稀疏的 DTW 距离矩阵以高效格式写入/读取至 Redis，
并存储个股特征向量指纹供增量引擎做 Cosine/Euclidean 检测。
"""
import json
import logging

import numpy as np

from cache.redis_client import RedisClient

logger = logging.getLogger(__name__)

# 7天过期，覆盖一个完整回测窗口
_MATRIX_TTL_SEC = 86400 * 7
_FINGERPRINT_TTL_SEC = 86400 * 7


class RedisSparseCacheManager:
    """
    管理 DTW 稀疏距离矩阵和特征向量指纹的 Redis 键值操作。
    Key 结构:
        距离矩阵对:  tick:dtw:{date}:{hash(s1,s2)}  -> float
        特征向量:    tick:feat:{date}:{stock_code}   -> json float list
    """

    def __init__(self, redis_client: RedisClient):
        self._redis = redis_client

    # ---------- 距离矩阵写入 / 读取 ----------

    async def save_sparse_matrix(
        self,
        date: str,
        stock_pairs: list[tuple[str, str]],
        distances: np.ndarray,
    ) -> int:
        """
        批量写入一组股票对距离到 Redis Pipeline。

        Returns:
            写入的键数量
        """
        client = await self._redis.get_client()
        pipe = client.pipeline()

        for (s1, s2), dist in zip(stock_pairs, distances, strict=False):
            pair_key = self._pair_key(date, s1, s2)
            pipe.set(pair_key, str(dist), ex=_MATRIX_TTL_SEC)

        await pipe.execute()
        logger.debug(f"[{date}] Sparse matrix saved: {len(stock_pairs)} pairs to Redis.")
        return len(stock_pairs)

    async def load_sparse_matrix(
        self,
        date: str,
        stock_pairs: list[tuple[str, str]],
    ) -> dict[tuple[str, str], float]:
        """
        批量读取指定股票对的距离缓存。
        缺失的键会被跳过（即需要重新计算）。

        Returns:
            { (s1, s2): distance } 字典（仅含缓存命中对）
        """
        client = await self._redis.get_client()
        pipe = client.pipeline()

        for s1, s2 in stock_pairs:
            pipe.get(self._pair_key(date, s1, s2))

        raw_values = await pipe.execute()

        result: dict[tuple[str, str], float] = {}
        for (s1, s2), val in zip(stock_pairs, raw_values, strict=False):
            if val is not None:
                try:
                    result[(s1, s2)] = float(val)
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse cached distance for ({s1},{s2}): {val}")

        hit_count = len(result)
        miss_count = len(stock_pairs) - hit_count
        logger.debug(f"[{date}] Matrix load: {hit_count} hits, {miss_count} misses.")
        return result

    # ---------- 特征向量指纹写入 / 读取 ----------

    async def save_feature_fingerprints(
        self, date: str, features: dict[str, np.ndarray]
    ) -> None:
        """批量存储各股票当日特征向量于 Redis，供次日增量检测使用。"""
        client = await self._redis.get_client()
        pipe = client.pipeline()

        for code, vec in features.items():
            key = self._fingerprint_key(date, code)
            pipe.set(key, json.dumps(vec.tolist()), ex=_FINGERPRINT_TTL_SEC)

        await pipe.execute()
        logger.debug(f"[{date}] Feature fingerprints saved: {len(features)} stocks.")

    async def load_feature_fingerprints(
        self, date: str, stock_codes: list[str]
    ) -> dict[str, np.ndarray | None]:
        """
        读取给定日期的特征向量指纹。
        若某只股票缺失，则对应值为 None。
        """
        client = await self._redis.get_client()
        pipe = client.pipeline()

        for code in stock_codes:
            pipe.get(self._fingerprint_key(date, code))

        raw_values = await pipe.execute()

        result: dict[str, np.ndarray | None] = {}
        for code, val in zip(stock_codes, raw_values, strict=False):
            if val is not None:
                try:
                    result[code] = np.array(json.loads(val), dtype=np.float32)
                except (json.JSONDecodeError, ValueError):
                    result[code] = None
            else:
                result[code] = None

        return result

    # ---------- 内部工具 ----------

    @staticmethod
    def _pair_key(date: str, s1: str, s2: str) -> str:
        """确保对称性：always use sorted order"""
        a, b = (s1, s2) if s1 <= s2 else (s2, s1)
        return f"tick:dtw:{date}:{a}:{b}"

    @staticmethod
    def _fingerprint_key(date: str, code: str) -> str:
        return f"tick:feat:{date}:{code}"
