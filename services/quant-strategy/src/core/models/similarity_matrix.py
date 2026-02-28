import numpy as np
from pydantic import BaseModel, ConfigDict  # type: ignore
from typing import List, Tuple

class SimilarityMatrix(BaseModel):
    """稀疏距离矩阵模型
    
    用于存储两个阶段相似度计算的结果：
    1. stock_pairs: 保存符合阈值相似度条件的股票代码对
    2. distances: 对应的距离值 (通常归一化至 [0, 1])
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    stock_pairs: List[Tuple[str, str]]
    distances: np.ndarray

    def to_adjacency_matrix(self, threshold: float = 0.3) -> None:
        """将稀疏矩阵转换为邻接矩阵（例如后续图论算法的输入格式）"""
        # Placeholder for community detection graph conversion logic
        pass
