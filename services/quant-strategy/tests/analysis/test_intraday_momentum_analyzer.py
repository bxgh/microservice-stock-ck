from datetime import datetime

from analysis.intraday.models import IntradaySignalType
from analysis.intraday.momentum_analyzer import IntradayMomentumAnalyzer
from models.signal import SignalType


def test_analyze_overnight_gap_fade():
    """测试量缩高开，博弈回归（做空预警）"""
    analyzer = IntradayMomentumAnalyzer(gap_threshold=0.02, volume_ratio_threshold=1.5)

    current_time = datetime(2025, 1, 1, 10, 0)
    # 高开 3% 但早盘缩量（VolumeRatio = 1.0 < 1.5）
    signal = analyzer.analyze_overnight_gap(
        "000001", current_time,
        yesterday_close=10.0,
        open_price=10.30,  # +3%
        volume_first_30m=1000,
        volume_avg_20d=1000
    )

    assert signal is not None
    assert signal.signal_type == IntradaySignalType.GAP_FADE
    assert signal.direction == SignalType.SHORT  # 诱多，回归看跌
    assert "量缩" in signal.reason

def test_analyze_overnight_breakaway_gap():
    """测试放量高开，追高动量 (GAP_FOLLOW)"""
    analyzer = IntradayMomentumAnalyzer(gap_threshold=0.02, volume_ratio_threshold=1.5)

    current_time = datetime(2025, 1, 1, 10, 0)
    # 高开 3% 且早盘巨量（VolumeRatio = 3.0 > 2.0 (1.5+0.5)）
    signal = analyzer.analyze_overnight_gap(
        "000002", current_time,
        yesterday_close=10.0,
        open_price=10.30,  # +3%
        volume_first_30m=3000,
        volume_avg_20d=1000
    )

    assert signal is not None
    assert signal.signal_type == IntradaySignalType.GAP_FOLLOW
    assert signal.direction == SignalType.LONG
    assert "跳空放量突破" in signal.reason

def test_analyze_momentum_transmission():
    """测试群落内部的补涨传导逻辑"""
    analyzer = IntradayMomentumAnalyzer()
    current_time = datetime(2025, 1, 1, 10, 0)

    # 龙头拉升 4%，小弟仅微涨 0.5% (符合拉升>3%, 小弟<1%)
    signal = analyzer.analyze_momentum_transmission(
        follower_code="000003",
        current_time=current_time,
        leader_code="000008",
        leader_intraday_return=0.04,
        follower_intraday_return=0.005,
        cluster_id=1
    )

    assert signal is not None
    assert signal.signal_type == IntradaySignalType.MOMENTUM_LAG
    assert signal.leader_stock == "000008"
    assert signal.cluster_id == 1

    # 因为相差了 0.035，得分 = 70 + 0.035*500 = 87.5
    assert signal.confidence_score == 87.5

def test_no_signal_for_normal_fluctuation():
    """普通波动不乱发信号"""
    analyzer = IntradayMomentumAnalyzer(gap_threshold=0.02, volume_ratio_threshold=1.5)
    current_time = datetime(2025, 1, 1, 10, 0)

    # 平开，量平
    signal = analyzer.analyze_overnight_gap(
        "000004", current_time,
        yesterday_close=10.0, open_price=10.05,
        volume_first_30m=1000, volume_avg_20d=1000
    )
    assert signal is None

    # 群落小弟也拉升了 3.5%（不符合滞涨标准）
    lag_signal = analyzer.analyze_momentum_transmission(
        follower_code="000005", current_time=current_time,
        leader_code="000006",
        leader_intraday_return=0.04,
        follower_intraday_return=0.035,
        cluster_id=1
    )
    assert lag_signal is None
