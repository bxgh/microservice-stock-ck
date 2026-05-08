"""
异动评分服务 (Anomaly Scoring Service)
实现 L8 异动股评分逻辑，支持从 get-stockdata 动态加载权重配置。
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
import pandas as pd

from adapters.stock_data_provider import data_provider

logger = logging.getLogger(__name__)

class AnomalyScoringService:
    """
    异动评分核心服务
    """

    def __init__(self, version: str = "v1"):
        self.version = version
        self.weights: Dict[str, float] = {}
        self.initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self):
        """初始化：从 API 加载权重配置"""
        if self.initialized:
            return

        async with self._lock:
            if self.initialized:
                return

        logger.info(f"Initializing AnomalyScoringService with version={self.version}...")
        
        try:
            # 从 get-stockdata 获取权重
            weight_data = await data_provider.get_anomaly_weights(self.version)
            
            # 如果 weight_data 是 {"version": "v1", "weights": {...}}
            if isinstance(weight_data, dict) and 'weights' in weight_data:
                self.weights = weight_data['weights']
            else:
                self.weights = weight_data # 兜底

            if not self.weights:
                logger.warning(f"⚠️ 未能加载到版本为 {self.version} 的异动权重，将使用默认极简权重")
                self.weights = {
                    "score_pct_chg": 0.3,
                    "score_volume": 0.3,
                    "score_event": 0.2,
                    "score_position": 0.2
                }
            
            # AC1 要求：日志中出现 using version=v1 及其对应权重值
            logger.info(f"[anomaly_score] using version={self.version} weights: {self.weights}")
            self.initialized = True
            logger.info("✅ AnomalyScoringService initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize AnomalyScoringService: {e}")
            # 容错：使用默认权重
            self.weights = {
                "score_pct_chg": 0.3,
                "score_volume": 0.3,
                "score_event": 0.2,
                "score_position": 0.2
            }
            self.initialized = True

    async def calculate_composite_score(self, component_scores: Dict[str, float]) -> float:
        """
        根据权重计算综合评分
        
        Args:
            component_scores: 各维度原始评分 {score_pct_chg: 80, ...}
            
        Returns:
            float: 综合得分 (0-100)
        """
        if not self.initialized:
            await self.initialize()

        total_score = 0.0
        for key, weight in self.weights.items():
            if key in component_scores:
                total_score += component_scores[key] * weight
        
        return round(total_score, 2)

    async def batch_score_stocks(self, stocks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量计算股票评分 (用于跑批任务)
        """
        if not self.initialized:
            await self.initialize()
            
        results = []
        for stock in stocks_data:
            # 提取各维度分数
            scores = {
                "score_pct_chg": stock.get("score_pct_chg", 0),
                "score_volume": stock.get("score_volume", 0),
                "score_event": stock.get("score_event", 0),
                "score_position": stock.get("score_position", 0)
            }
            composite = await self.calculate_composite_score(scores)
            
            # 构造结果
            result = stock.copy()
            result["composite_score"] = composite
            result["source_version"] = self.version
            results.append(result)
            
        return results

# 全局单例 (默认 v1)
anomaly_scoring_service = AnomalyScoringService(version="v1")
