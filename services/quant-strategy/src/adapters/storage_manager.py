
import logging
import os

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

class StorageManager:
    """
    高性能矩阵与特征存储管理器 (PyArrow/Parquet)
    """
    def __init__(self, base_dir: str = "data/matrix"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def save_similarity_matrix(self, trade_date: str, similarity_results: dict[tuple[int, int], float]):
        """
        将稀疏相似度矩阵保存为 Parquet
        """
        if not similarity_results:
            return

        file_path = os.path.join(self.base_dir, f"sim_matrix_{trade_date}.parquet")

        # 转换为 DataFrame
        pairs = list(similarity_results.keys())
        df = pd.DataFrame({
            'idx_i': [p[0] for p in pairs],
            'idx_j': [p[1] for p in pairs],
            'dist': list(similarity_results.values())
        })

        table = pa.Table.from_pandas(df)
        pq.write_table(table, file_path, compression='snappy')
        logger.info(f"✅ Similarity matrix saved to {file_path} ({len(df)} pairs)")

    def load_similarity_matrix(self, trade_date: str) -> dict[tuple[int, int], float]:
        """
        从 Parquet 加载相似度矩阵
        """
        file_path = os.path.join(self.base_dir, f"sim_matrix_{trade_date}.parquet")
        if not os.path.exists(file_path):
            return {}

        table = pq.read_table(file_path)
        df = table.to_pandas()

        results = {}
        for _, row in df.iterrows():
            results[(int(row['idx_i']), int(row['idx_j']))] = float(row['dist'])

        logger.info(f"✅ Similarity matrix loaded from {file_path} ({len(results)} pairs)")
        return results

    def use_memmap(self, shape: tuple[int, int], dtype=np.float32, filename: str = "temp_matrix.dat"):
        """
        创建内存映射矩阵以处理 OOM
        """
        path = os.path.join(self.base_dir, filename)
        return np.memmap(path, dtype=dtype, mode='w+', shape=shape)
