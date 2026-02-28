import logging
from typing import Any

logger = logging.getLogger(__name__)

class TickClusterMetrics:
    """
    横截面微积分性能与容量监控指标
    """
    def __init__(self):
        self.feature_compute_time = 0.0
        self.dtw_compute_time = 0.0
        self.cluster_compute_time = 0.0

        self.total_stocks = 0
        self.total_pairs_computed = 0
        self.num_clusters_found = 0

        # Incremental engine spec
        self.total_changed_stocks = 0
        self.cache_hit_pairs = 0

    def report(self) -> dict[str, Any]:
        """输出 Grafana 或 Logging 需要的埋点字典"""
        payload = {
            "feature_compute_time_sec": self.feature_compute_time,
            "dtw_compute_time_sec": self.dtw_compute_time,
            "cluster_compute_time_sec": self.cluster_compute_time,
            "total_time_sec": self.feature_compute_time + self.dtw_compute_time + self.cluster_compute_time,

            "stocks_processed": self.total_stocks,
            "changed_stocks_detected": self.total_changed_stocks,

            "new_dtw_pairs_computed": self.total_pairs_computed,
            "cached_pairs_reused": self.cache_hit_pairs,

            "clusters_found": self.num_clusters_found,
            "pairs_per_second": self.total_pairs_computed / self.dtw_compute_time if self.dtw_compute_time > 0 else 0,
        }

        logger.info(f"TickCluster performance metrics generated: Total Time {payload['total_time_sec']:.2f}s, Reused Pairs {payload['cached_pairs_reused']}")
        return payload
