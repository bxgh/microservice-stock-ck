import logging
import pandas as pd
from typing import Optional

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from config.settings import settings

logger = logging.getLogger(__name__)


class AltDataDAO:
    """
    提取和落盘另类数据指标 (生态监控) 的 DAO。
    对应 GSF Part 1 中读取非结构化行情外的外部信号结构。
    """
    
    def __init__(self):
        self.host = settings.QS_CLICKHOUSE_HOST
        self.port = settings.QS_CLICKHOUSE_PORT  # 应为 HTTP 8123
        self.user = settings.QS_CLICKHOUSE_USER
        self.password = settings.QS_CLICKHOUSE_PASSWORD
        self.database = settings.QS_CLICKHOUSE_ALTDATA_DB
        self._client: Optional[Client] = None

    def _get_client(self) -> Client:
        if not self._client:
            self._client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                database=self.database,
            )
        return self._client

    def get_raw_metrics(self, label: str, lookback_days: int = 45) -> pd.DataFrame:
        """
        获取指定标签（即某个技术生态）过去一段时间汇总回来的全量活跃记录。
        获取 Pandas DataFrame 直接支持后续向量运算。
        """
        client = self._get_client()
        query = f"""
            SELECT
                collect_time,
                org,
                repo,
                label,
                pr_merged_count,
                pr_merged_acceleration,
                issue_close_median_hours,
                star_delta_7d,
                commit_count_7d,
                contributor_count_30d
            FROM github_repo_metrics
            WHERE label = %(label)s
              AND collect_time >= now() - INTERVAL %(lookback)s DAY
            ORDER BY collect_time ASC
        """
        
        try:
            df = client.query_df(
                query,
                parameters={"label": label, "lookback": lookback_days}
            )
            return df
        except Exception as e:
            logger.error(f"Failed to fetch raw metrics for {label} from ClickHouse: {e}")
            # 返回具备同等胸膛的空 DataFrame 保障策略端不会崩溃
            return pd.DataFrame(columns=[
                "collect_time", "org", "repo", "label", "pr_merged_count",
                "pr_merged_acceleration", "issue_close_median_hours", 
                "star_delta_7d", "commit_count_7d", "contributor_count_30d"
            ])

    def insert_signals(self, signals_df: pd.DataFrame):
        """
        将聚类好的综合生态信号（含 Z-Score 解析）落地储存回 ClickHouse。
        """
        if signals_df is None or signals_df.empty:
            return
            
        required_cols = [
            "signal_time", "label", "composite_z_score", 
            "dominant_factor", "signal_level", "detail"
        ]
        
        for col in required_cols:
            if col not in signals_df.columns:
                logger.error(f"Missing required col `{col}` in signal insert.")
                return
                
        # ClickHouse Numpy 插入仅需保证列顺序准确对齐
        df_target = signals_df[required_cols]
        client = self._get_client()
        
        try:
            client.insert_df(
                table="ecosystem_signals",
                df=df_target,
                database=self.database
            )
            logger.info(f"Successfully inserted {len(df_target)} eco signals back to ClickHouse.")
        except Exception as e:
            logger.error(f"Failed to insert ecosystem signals: {e}")

    def get_active_signals(self) -> pd.DataFrame:
        """
        获取当日最近一次计算出来的生态活跃大信号 (排除 NEUTRAL)。
        供策略打分选股阶段调用加分。
        """
        client = self._get_client()
        query = f"""
            SELECT label, composite_z_score, dominant_factor, signal_level
            FROM ecosystem_signals
            WHERE signal_time >= today() - INTERVAL 1 DAY
              AND signal_level IN ('WARM', 'HOT', 'EXTREME')
        """
        try:
            return client.query_df(query)
        except Exception as e:
            logger.error(f"Failed to fetch active eco signals: {e}")
            return pd.DataFrame(columns=["label", "composite_z_score", "dominant_factor", "signal_level"])

    def get_hardware_spot_stats(self, lookback_days: int = 7) -> pd.DataFrame:
        """
        获取最近一段时间的 GPU 现货价格波动统计 (Story 18.3)
        """
        client = self._get_client()
        query = f"""
            SELECT platform, gpu_model, 
                   avg(price_per_hour) as avg_price, 
                   max(availability) as max_avail
            FROM hardware_spot_prices
            WHERE collect_time >= now() - INTERVAL %(lookback)s DAY
            GROUP BY platform, gpu_model
        """
        try:
            return client.query_df(query, parameters={"lookback": lookback_days})
        except Exception as e:
            logger.error(f"Failed to fetch hardware spot stats: {e}")
            return pd.DataFrame()

    def get_procurement_capex_signals(self, lookback_days: int = 7) -> pd.DataFrame:
        """
        获取最近一段时间的政企算力投资脉冲 (Story 18.3)
        """
        client = self._get_client()
        query = f"""
            SELECT hardware_type, sum(amount) as total_amount, count() as tender_count
            FROM hardware_procurement_capex
            WHERE date >= today() - INTERVAL %(lookback)s DAY
            GROUP BY hardware_type
            HAVING total_amount > 0
        """
        try:
            return client.query_df(query, parameters={"lookback": lookback_days})
        except Exception as e:
            logger.error(f"Failed to fetch procurement capex signals: {e}")
            return pd.DataFrame()
