
import json
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from adapters.clickhouse_loader import ClickHouseLoader
from cache.feature_store import FeatureStore
from cache.redis_client import redis_client
from core.analysis.clustering_engine import ClusteringEngine
from core.analysis.lead_lag_analyzer import LeadLagAnalyzer
from core.analysis.similarity_engine import SimilarityEngine

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
        stock_universe: list[str],
        benchmark_code: str = "000300",
        threshold_percentile: float = 5.0,
        prefilter_percentile: float = 0.05,
        clustering_method: str = "leiden"
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

        # --- 增量计算逻辑 (Story 004.02) ---
        # 1. 尝试获取昨日特征以计算指纹
        yesterday = (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        past_features_dict = await self.feature_store.batch_get(active_stocks, yesterday)

        stable_stocks = set()
        if past_features_dict:
            # 组合所有列作为指纹 (简化：取前3列 A/B/C)
            curr_all = np.array([features_dict[s][:, :3].flatten() for s in active_stocks])
            past_all = np.array([past_features_dict[s][:, :3].flatten() if s in past_features_dict else np.zeros_like(features_dict[s][:, :3].flatten()) for s in active_stocks])
            stable_stocks = self.similarity_engine.identify_stable_stocks(curr_all, past_all)

        # 2. 尝试加载昨日相似度结果
        from adapters.storage_manager import StorageManager
        storage = StorageManager()
        past_sim_results = storage.load_similarity_matrix(yesterday)
        # ----------------------------------

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

        # --- 增量过滤 (Story 004.02) ---
        dtw_results = {}
        to_compute = []

        for i, j in candidates:
            # 对应的代码
            active_stocks[i]
            active_stocks[j]

            # 规则：如果两只股票都稳定，且昨日已有计算结果，则复用
            if i in stable_stocks and j in stable_stocks and (i, j) in past_sim_results:
                dtw_results[(i, j)] = past_sim_results[(i, j)]
            else:
                to_compute.append((i, j))

        logger.info(f"Incremental filtering: reuse {len(dtw_results)}, compute {len(to_compute)}")

        # --- 断点续传逻辑 (Story 004.02) ---
        checkpoint_key = f"qs:checkpoint:{trade_date}"
        from cache.redis_client import redis_client
        client = await redis_client.get_client()

        # 加载已有的断点数据
        cached_results_raw = await client.hgetall(checkpoint_key)
        cached_results = {tuple(map(int, k.decode().split(':'))): float(v) for k, v in cached_results_raw.items()}
        dtw_results.update(cached_results)

        # 排除已计算的
        final_to_compute = [p for p in to_compute if p not in dtw_results]

        logger.info(f"Checkpoint check: resumed {len(cached_results)}, final to compute {len(final_to_compute)}")

        if final_to_compute:
            # 分批计算并存入 Checkpoint
            batch_size = 5000 # 约 100 只股票对应的对数
            for i in range(0, len(final_to_compute), batch_size):
                batch = final_to_compute[i : i + batch_size]
                new_dtw = await self.similarity_engine.compute_dtw_parallel(
                    batch, feat_a, feat_b, feat_c
                )
                dtw_results.update(new_dtw)

                # 同步到 Redis Checkpoint
                serialized_batch = {f"{k[0]}:{k[1]}": v for k, v in new_dtw.items()}
                if serialized_batch:
                    await client.hset(checkpoint_key, mapping=serialized_batch)

        # 最终保存到 Parquet 后清理 Checkpoint
        storage.save_similarity_matrix(trade_date, dtw_results)
        await client.delete(checkpoint_key)
        # ----------------------------------

        # 4. 聚类分析 (ClusteringEngine)
        G = self.clustering_engine.build_similarity_graph(
            active_stocks, dtw_results, percentile=threshold_percentile
        )
        # 社区发现
        partition = self.clustering_engine.detect_communities(G, method=clustering_method)
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
            # 获取当前簇的收益率和 OBI 特征
            cluster_returns = {s: features_dict[s][:, 2] for s in members if s in features_dict}
            cluster_obi = {s: features_dict[s][:, 1] for s in members if s in features_dict}

            # 构建领先图 (降低阈值以适应小样本/真实噪声)
            lead_lag_graph = self.lead_lag_analyzer.build_lead_lag_graph(
                members, cluster_returns, corr_threshold=0.3, min_lag_threshold=1
            )

            # 基础龙头识别 (PageRank)
            raw_leaders = self.lead_lag_analyzer.identify_leader(lead_lag_graph)

            # OBI 动量增强推荐
            final_leaders = self.lead_lag_analyzer.enhance_with_obi_momentum(raw_leaders, cluster_obi)

            # 计算分歧度与趋势阶段
            divergence_series = self.lead_lag_analyzer.compute_divergence(members, cluster_returns)
            current_div = divergence_series[-1] if len(divergence_series) > 0 else 0

            # TODO: 这里需要持久化的历史分歧度数据来判定 Phase，目前先使用当前序列的 20/80 分位模拟
            phase = self.lead_lag_analyzer.classify_trend_phase(current_div, divergence_series)

            analysis_report.append({
                "cluster_id": cid,
                "members": members,
                "leaders": final_leaders,
                "current_divergence": current_div,
                "trend_phase": phase.value,
                "count": len(members)
            })

        # 5. 存储结果
        await self.save_analysis_results(trade_date, analysis_report)

        # 6. 发布事件通知策略层 (EPIC-005)
        from core.event_bus import EventBus
        bus = EventBus()
        await bus.publish("market_analysis_completed", {
            "trade_date": trade_date,
            "report": analysis_report
        })

        logger.info(f"✅ Market analysis completed and event published. Found {len(analysis_report)} valid clusters.")
        return analysis_report

    async def save_analysis_results(self, trade_date: str, report: list[dict]):
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
                logger.error("Failed to save analysis report to Redis")
        except Exception as e:
            logger.error(f"Failed to save analysis report to Redis: {e}")

        # ClickHouse 存证
        if not report:
            return

        from config.settings import settings
        table = settings.QS_CLICKHOUSE_ANALYTICS_TABLE

        # 准备数据格式: (trade_date, cluster_id, members, leaders, avg_divergence, member_count, trend_phase, updated_at)
        data = []
        now = datetime.now()
        for item in report:
            # members: List[str] -> Array(String)
            # leaders: List[Tuple[str, float]] -> Array(Tuple(String, Float64))
            # 强化转换: 确保所有 NumPy 类型被剥离
            pure_leaders = []
            for l in item["leaders"]:
                if isinstance(l, (list, tuple)):
                    pure_leaders.append((str(l[0]), float(l[1])))
                else:
                    pure_leaders.append((str(l), 1.0))

            phase = item.get("trend_phase", "Steady")

            data.append((
                datetime.strptime(trade_date, "%Y-%m-%d").date(),
                int(item["cluster_id"]),
                [str(m) for m in item["members"]],
                pure_leaders,
                float(item["current_divergence"]),
                int(item["count"]),
                str(phase),
                now
            ))

        # 彻底转换为纯 Python 类型以解决 ClickHouse Driver 的 NumPy 报错
        final_data = []
        for row in data:
            pure_row = []
            for item in row:
                if isinstance(item, np.generic):
                    pure_row.append(item.item())
                elif isinstance(item, list):
                    pure_row.append([x.item() if isinstance(x, np.generic) else x for x in item])
                elif isinstance(item, tuple):
                    pure_row.append(tuple(x.item() if isinstance(x, np.generic) else x for x in item))
                else:
                    pure_row.append(item)
            final_data.append(tuple(pure_row))

        try:
            async with self.loader._lock:
                self.loader.client.execute(
                    f"INSERT INTO {table} VALUES",
                    final_data
                )
            logger.info(f"✅ {len(final_data)} clusters saved to ClickHouse table {table}")
        except Exception as e:
            logger.error(f"Failed to save analysis results to ClickHouse: {e}")

    async def _get_benchmark_returns(self, code: str, date: str) -> np.ndarray:
        """获取大盘基准收益率 (240维)"""
        try:
            # 1. 获取快照
            df = await self.loader.get_snapshots(code, date)

            # 定义完整的交易分钟索引 (Gate-3 对齐标准)
            morning_range = pd.date_range(f"{date} 09:30:00", f"{date} 11:30:00", freq="1min")
            afternoon_range = pd.date_range(f"{date} 13:00:00", f"{date} 15:00:00", freq="1min")
            morning_range.union(afternoon_range)
            # 注意: union 后的 full_range 包含 11:31 和 13:00 等边缘，总计通常是 121 + 121 - 1?
            # 实际上 A 股交易分钟是 9:30-11:30 (121点), 13:01-15:00 (120点), 共 241 点。
            # 策略要求 240 维，通常取 (09:31-11:30) 和 (13:01-15:00)。

            target_range = pd.date_range(f"{date} 09:31:00", f"{date} 11:30:00", freq="1min").union(
                pd.date_range(f"{date} 13:01:00", f"{date} 15:00:00", freq="1min")
            )

            if df.empty:
                logger.warning(f"Benchmark data empty for {code} on {date}. Using zeros.")
                return np.zeros(240)

            # 2. 预处理时间列
            df['snapshot_time'] = pd.to_datetime(df['snapshot_time'])
            df = df.sort_values('snapshot_time')

            # 3. 重采样并填充
            df = df.set_index('snapshot_time')
            # 这里的 current_price 是关键
            resampled = df['current_price'].resample('1min').last().reindex(target_range).ffill().bfill()

            # 4. 计算收益率
            prices = resampled.values
            if len(prices) < 2:
                return np.zeros(240)

            returns = np.zeros(len(prices))
            # 收益率计算: (P_t - P_t-1) / P_t-1
            returns[1:] = np.diff(prices) / prices[:-1]
            returns = np.nan_to_num(returns, nan=0.0, posinf=0.0, neginf=0.0)

            # 确保 240 维
            if len(returns) > 240:
                return returns[:240]
            elif len(returns) < 240:
                return np.pad(returns, (0, 240 - len(returns)))
            return returns

        except Exception as e:
            logger.error(f"Failed to fetch benchmark returns: {e}")
            return np.zeros(240)

    async def close(self):
        await self.similarity_engine.close()
        await self.clustering_engine.close()
        await self.lead_lag_analyzer.close()
        await self.loader.close()

