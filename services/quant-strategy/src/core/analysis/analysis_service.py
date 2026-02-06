
import logging
import asyncio
import numpy as np
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
import pandas as pd

from core.analysis.similarity_engine import SimilarityEngine
from core.analysis.clustering_engine import ClusteringEngine
from core.analysis.lead_lag_analyzer import LeadLagAnalyzer
from cache.feature_store import FeatureStore
from cache.redis_client import redis_client
from adapters.clickhouse_loader import ClickHouseLoader
import json

logger = logging.getLogger(__name__)

class AnalysisService:
    """
    核心分析服务 (Epic Part 2 Orchestrator)
    实现全市场相关性发现、社区划分与龙头识别。
    """
    def __init__(self, num_workers: int = 8):
        self.similarity_engine = SimilarityEngine(num_workers=num_workers)
        self.clustering_engine = ClusteringEngine()
        self.lead_lag_analyzer = LeadLagAnalyzer()
        self.feature_store = FeatureStore()
        self.loader = ClickHouseLoader()

    async def initialize(self):
        await self.similarity_engine.initialize()
        await self.clustering_engine.initialize()
        await self.lead_lag_analyzer.initialize()
        await self.loader.initialize()
        logger.info("🚀 AnalysisService initialized")

    async def run_market_analysis(
        self, 
        trade_date: str, 
        stock_universe: List[str], 
        benchmark_code: str = "000300",
        threshold_percentile: float = 5.0,
        prefilter_percentile: float = 0.05
    ):
        """
        全量分析流程
        """
        logger.info(f"📊 Starting market analysis for {trade_date} ({len(stock_universe)} stocks)")
        
        # 1. 批量加载特征
        # Order: [vec_a, vec_b, vec_c, ...]
        features_dict = await self.feature_store.batch_get(stock_universe, trade_date)
        if not features_dict:
            logger.error("❌ No features found in FeatureStore")
            return None
            
        active_stocks = sorted(features_dict.keys())
        logger.info(f"Loaded features for {len(active_stocks)} stocks")
        
        # 提取向量 A, B, C (前 3 列)
        # 每个向量形状为 (240,)
        feat_a = np.array([features_dict[s][:, 0] for s in active_stocks])
        feat_b = np.array([features_dict[s][:, 1] for s in active_stocks])
        feat_c = np.array([features_dict[s][:, 2] for s in active_stocks])
        
        # 2. 相似度计算 (SimilarityEngine)
        # 第一阶段: 粗筛
        candidates = self.similarity_engine.euclidean_prefilter(
            feat_a, feat_b, feat_c, top_k_percent=prefilter_percentile
        )
        logger.info(f"Euclidean pre-filter kept {len(candidates)} candidates")
        
        dtw_results = await self.similarity_engine.compute_dtw_parallel(
            candidates, feat_a, feat_b, feat_c
        )
        logger.info(f"DTW calculation completed for {len(dtw_results)} pairs")
        
        # 3. 聚类分析 (ClusteringEngine)
        G = self.clustering_engine.build_similarity_graph(
            active_stocks, dtw_results, percentile=threshold_percentile
        )
        # 社区发现
        partition = self.clustering_engine.detect_communities(G)
        logger.info(f"Louvain detected {len(set(partition.values()))} raw communities")
        
        # 加载大盘数据用于过滤
        benchmark_returns = await self._get_benchmark_returns(benchmark_code, trade_date)
        
        # 提取收益率字典用于过滤和分析
        returns_dict = {s: features_dict[s][:, 2] for s in active_stocks}
        
        # 噪音过滤
        filtered_clusters = await self.clustering_engine.filter_noise_clusters(
            partition, active_stocks, returns_dict, benchmark_returns
        )
        logger.info(f"Filtered clusters remaining: {len(filtered_clusters)}")
        
        # 4. 龙头与时滞分析 (LeadLagAnalyzer)
        analysis_report = []
        for cid, members in filtered_clusters.items():
            # 构建领先图
            lead_lag_graph = self.lead_lag_analyzer.build_lead_lag_graph(members, returns_dict)
            # 识别龙头
            leaders = self.lead_lag_analyzer.identify_leader(lead_lag_graph)
            # 计算分歧度
            divergence = self.lead_lag_analyzer.compute_divergence(members, returns_dict)
            
            # TODO: 跨日稳定性加载与评估
            
            analysis_report.append({
                "cluster_id": cid,
                "members": members,
                "leaders": leaders,
                "current_divergence": divergence[-1] if len(divergence) > 0 else 0,
                "count": len(members)
            })
            
        # 5. 存储结果
        await self.save_analysis_results(trade_date, analysis_report)
            
        logger.info(f"✅ Market analysis completed. Found {len(analysis_report)} valid clusters.")
        return analysis_report

    async def save_analysis_results(self, trade_date: str, report: List[Dict]):
        """
        持久化分析结果
        1. 详细结果存入 Redis (供 API 实时查询)
        2. 结构化汇总存入 ClickHouse (长期存证)
        """
        # Redis Key
        redis_key = f"qs:analysis:{trade_date}:report"
        try:
            success = await redis_client.set(redis_key, json.dumps(report, ensure_ascii=False), ttl=86400 * 7)
            if success:
                logger.info(f"✅ Analysis report for {trade_date} saved to Redis")
            else:
                logger.error(f"Failed to save analysis report to Redis (Reason: Unknown)")
        except Exception as e:
            logger.error(f"Failed to save analysis report to Redis: {e}")

        # TODO: ClickHouse 存证 (需要先定义表 schema)
        # 字段: trade_date, cluster_id, members, leader, score, divergence
        pass

    async def _get_benchmark_returns(self, code: str, date: str) -> np.ndarray:
        """获取大盘基准收益率 (240维)"""
        try:
            # 1. 获取快照
            # 指数代码通常为 "sh000300" 或 "000300"
            # Loader 会自动处理前缀清洗 (DataValidator.clean_stock_code)
            
            df = await self.loader.get_snapshots(code, date)
            
            if df.empty:
                logger.warning(f"Benchmark data empty for {code} on {date}. '000001' is Ping An Bank, not Index, so no fallback used. Using zeros.")
                return np.zeros(240)
            
            # 2. 预处理时间列
            df['snapshot_time'] = pd.to_datetime(df['snapshot_time'])
            df = df.sort_values('snapshot_time')
            
            # 3. 重采样到 1 分钟 (240 个点)
            # 定义完整的交易分钟索引
            morning_range = pd.date_range(f"{date} 09:30:00", f"{date} 11:30:00", freq="1min")
            afternoon_range = pd.date_range(f"{date} 13:00:00", f"{date} 15:00:00", freq="1min")
            full_range = morning_range.union(afternoon_range)
            
            # 设置索引并重采样
            df = df.set_index('snapshot_time')
            # 使用 forward fill 填充空缺分钟 (指数数据通常较密)
            resampled = df['current_price'].resample('1min').last().reindex(full_range).ffill().bfill()
            
            # 4. 计算收益率
            prices = resampled.values
            # 简单收益率: (P_t - P_t-1) / P_t-1
            # 第一个点设为 0
            returns = np.zeros(len(prices))
            returns[1:] = np.diff(prices) / prices[:-1]
            # 处理可能的 nan/inf
            returns = np.nan_to_num(returns, nan=0.0, posinf=0.0, neginf=0.0)
            
            # 截取前 240 个点
            if len(returns) > 240:
                 returns = returns[:240]
            elif len(returns) < 240:
                 returns = np.pad(returns, (0, 240 - len(returns)))
                 
            return returns

        except Exception as e:
            logger.error(f"Failed to fetch benchmark returns: {e}")
            return np.zeros(240)

    async def close(self):
        await self.similarity_engine.close()
        await self.clustering_engine.close()
        await self.lead_lag_analyzer.close()
        await self.loader.close()

