
import pytest
import numpy as np
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock, patch
from core.analysis.analysis_service import AnalysisService

class TestAnalysisPipeline:
    @pytest.fixture
    def service(self):
        # 设置全局日志级别为 INFO
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("core.analysis.analysis_service").setLevel(logging.INFO)
        return AnalysisService(num_workers=2)

    @pytest.mark.asyncio
    async def test_run_market_analysis_flow(self, service):
        """测试全流程集成 (Mocked I/O)"""
        trade_date = "2026-02-05"
        # 10 只股票
        stock_universe = [f"Stock_{i}" for i in range(10)]
        
        # 构造 Mock 特征 (10 stocks, 240 mins, 9 features)
        # 使用平滑的正弦波，这样 Euclidean 距离对时滞不敏感 (Lag 1 -> Cosine -> Small Dist)
        t = np.linspace(0, 4*np.pi, 240)
        base = np.zeros((240, 9))
        for k in range(9):
             base[:, k] = np.sin(t + k) # 每一列相位不同
             
        mock_features = {}
        for i in range(10):
            if i == 0:
                mock_features["Stock_0"] = base
            elif i == 1:
                # Stock_1 滞后 Stock_0 2个时间步 (平滑信号下 Euclidean 距离依然很小)
                feat = np.zeros((240, 9))
                feat[2:] = base[:-2]
                mock_features["Stock_1"] = feat + np.random.randn(240, 9) * 0.001
            elif i == 2:
                # Stock_2 滞后 Stock_0 4个时间步
                feat = np.zeros((240, 9))
                feat[4:] = base[:-4]
                mock_features["Stock_2"] = feat + np.random.randn(240, 9) * 0.001
            else:
                # 随机组 (白噪声，Euclidean 距离会很大)
                mock_features[f"Stock_{i}"] = np.random.randn(240, 9)

        # Patch 外部 I/O
        with patch("core.analysis.analysis_service.FeatureStore.batch_get", new_callable=AsyncMock) as mock_batch_get, \
             patch("core.analysis.analysis_service.redis_client.set", new_callable=AsyncMock) as mock_redis_set, \
             patch("core.analysis.analysis_service.ClickHouseLoader.initialize", new_callable=AsyncMock), \
             patch("core.analysis.analysis_service.ClickHouseLoader.close", new_callable=AsyncMock), \
             patch("core.analysis.analysis_service.AnalysisService._get_benchmark_returns", new_callable=AsyncMock) as mock_bench:
            
            mock_batch_get.return_value = mock_features
            mock_bench.return_value = np.random.randn(240)
            mock_redis_set.return_value = True
            
            # 运行分析 (使用 Leiden 算法)
            report = await service.run_market_analysis(
                trade_date, stock_universe, 
                threshold_percentile=100.0,
                prefilter_percentile=1.0,
                clustering_method="leiden"
            )
            
            # 验证结果
            assert report is not None
            assert len(report) >= 1
            
            # 验证 ClickHouse 写入被调用 (之前 Patch 了 execute)
            # 注意: ClickHouseLoader.client.execute 被调用了两次（DDL 和 Insert）
            # 在集成测试中，我们 Patch 了 initialize，但没有直接 Patch client.execute 在 service initialization 之后
            # 实际上在 test_run_market_analysis_flow 中，service 已经初始化了。
            
            # 检查第一个簇的成员
            found_cluster = False
            for cluster in report:
                members = set(cluster['members'])
                # Stock_0, 1, 2 应该是最相似的
                if "Stock_0" in members and "Stock_1" in members:
                    found_cluster = True
                    # 检查趋势阶段是否由 Enum 转换为了字符串
                    assert isinstance(cluster['trend_phase'], str)
                    # 检查龙头 (PageRank + OBI 增强后)
                    leaders = [L[0] for L in cluster['leaders']]
                    assert "Stock_0" in leaders
                    
            assert found_cluster, f"Failed to identify the correlated cluster S0/1. Report: {report}"

        await service.close()
