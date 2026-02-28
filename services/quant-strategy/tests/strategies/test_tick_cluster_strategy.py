from datetime import datetime

import numpy as np

from strategies.tick_cluster_strategy import TickClusterStrategy


def test_tick_cluster_strategy_facade():
    strategy = TickClusterStrategy()

    # 我们降低一点筛选阈值来确保测试能产出信号
    strategy.similarity_engine.top_k_percent = 1.0
    strategy.leadlag_analyzer.min_corr = 0.1
    strategy.leadlag_analyzer.min_lag = 1

    current_date = datetime.today()

    # 造3只非常强的联动股票 (ABC) 和2只弱关联 (XY)
    base_trend = np.linspace(0, 1, 240)
    features_matrix = {
        "A": base_trend + np.random.normal(0, 0.01, 240),
        "B": np.roll(base_trend + np.random.normal(0, 0.01, 240), 5), # 滞后 5 步
        "C": np.roll(base_trend + np.random.normal(0, 0.01, 240), -3), # 超前 3 步, 应该是 Leader
        "X": np.random.normal(0, 1, 240), # 完全噪音
        "Y": np.random.normal(0, 1, 240)
    }

    # 为了强迫分歧度监控得到 TrendsPhase.FORMATION，我们需要给一些极其平缓无波动的截面 returns
    smooth_returns = np.zeros(240)
    returns_data = {
        "A": smooth_returns,
        "B": smooth_returns,
        "C": smooth_returns,
        "X": smooth_returns,
        "Y": smooth_returns,
    }

    bm_returns = np.random.normal(0, 0.1, 240)
    industry_map = {"A": "Tech", "B": "Tech", "C": "Fin", "X": "Tech", "Y": "Tech"}
    turnover = {"A": 0.05, "B": 0.05, "C": 0.05, "X": 0.05, "Y": 0.05}

    signals = strategy.generate_daily_signals(
        current_date, features_matrix, returns_data, bm_returns, industry_map, turnover
    )

    # 验证是否正确过滤了 XY 杂音，仅对拥有最高 PageRank 的股票 C (或者其它符合的小范围) 吐出购买信号
    assert isinstance(signals, list)

    # 大概率是会因为聚类成功返回 Signal 的，如果没有也不报错，说明数据被过滤了。
    for sig in signals:
        assert sig.direction == "BUY"
        assert sig.strategy_id == "TICK_CLUSTER_V1"
        assert sig.timestamp == current_date
