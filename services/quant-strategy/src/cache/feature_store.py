
"""
特征存储模块 (FeatureStore)
负责将生成的特征矩阵 (Numpy) 压缩后存入 Redis
支持批量检索
"""
import io
import logging
import zlib

import numpy as np

from cache.redis_client import redis_client

logger = logging.getLogger(__name__)

class FeatureStore:
    def __init__(self, ttl: int = 86400 * 3): # 默认 3 天
        self.ttl = ttl
        self.KEY_PATTERN = "qs:feat:{date}:{code}"

    def _pack(self, data: np.ndarray) -> bytes:
        """
        压缩特征矩阵
        使用 numpy.save (处理维度和Dtype) + zlib
        """
        buffer = io.BytesIO()
        np.save(buffer, data)
        raw_bytes = buffer.getvalue()
        return zlib.compress(raw_bytes)

    def _unpack(self, compressed_bytes: bytes) -> np.ndarray:
        """
        解压特征矩阵
        """
        raw_bytes = zlib.decompress(compressed_bytes)
        buffer = io.BytesIO(raw_bytes)
        return np.load(buffer)

    async def save_features(self, stock_code: str, trade_date: str, features: np.ndarray) -> bool:
        """
        保存特征矩阵到 Redis
        """
        key = self.KEY_PATTERN.format(date=trade_date, code=stock_code)
        try:
            packed_data = self._pack(features)
            client = await redis_client.get_binary_client()
            await client.set(key, packed_data, ex=self.ttl)
            logger.info(f"✅ Features saved to Redis for {stock_code} on {trade_date} (Size: {len(packed_data)} bytes)")
            return True
        except Exception as e:
            logger.error(f"Failed to save features for {stock_code}: {e}")
            return False

    async def load_features(self, stock_code: str, trade_date: str) -> np.ndarray | None:
        """
        从 Redis 读取特征矩阵
        """
        key = self.KEY_PATTERN.format(date=trade_date, code=stock_code)
        try:
            client = await redis_client.get_binary_client()
            compressed_data = await client.get(key)
            if not compressed_data:
                return None

            return self._unpack(compressed_data)
        except Exception as e:
            logger.error(f"Failed to load features for {stock_code}: {e}")
            return None

    async def batch_get(self, stock_codes: list[str], trade_date: str) -> dict[str, np.ndarray]:
        """
        批量获取特征矩阵 (供 Part 2 DTW 使用)
        """
        if not stock_codes:
            return {}

        keys = [self.KEY_PATTERN.format(date=trade_date, code=c) for c in stock_codes]
        try:
            client = await redis_client.get_binary_client()
            raw_values = await client.mget(keys)

            result = {}
            for code, val in zip(stock_codes, raw_values, strict=False):
                if val:
                    result[code] = self._unpack(val)

            return result
        except Exception as e:
            logger.error(f"Batch get features failed: {e}")
            return {}
