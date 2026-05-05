import logging
from datetime import datetime

from analysis.intraday.models import IntradaySignal, IntradaySignalType
from models.signal import Priority, SignalType

logger = logging.getLogger(__name__)

class IntradayMomentumAnalyzer:
    """
    日内动量与隔夜跳空套利引擎。

    设计为盘中实时触发或高频回测阶段循环触发。
    分析前日收盘 -> 今日开盘的跳空 (Gap) 方向，叠加开盘 30 分钟大单资金量 (VolumeRatio)，
    裁定是属于追涨 (Follow) 还是均值回归 (Fade)。
    以及利用同集群龙头股的拉皮条效应进行补涨收割 (Momentum Transmission).
    """

    def __init__(self, gap_threshold: float = 0.02, volume_ratio_threshold: float = 1.5):
        """
        Args:
            gap_threshold: 设置多大的跳空幅步被视为异常（默认 2%）
            volume_ratio_threshold: 前 30 分钟相对前 20 天同期的放量倍数
        """
        self.gap_threshold = gap_threshold
        self.volume_ratio_threshold = volume_ratio_threshold

    def analyze_overnight_gap(
        self,
        stock_code: str,
        current_time: datetime,
        yesterday_close: float,
        open_price: float,
        volume_first_30m: float,
        volume_avg_20d: float
    ) -> IntradaySignal | None:
        """
        检测隔夜跳空与开盘 30 分钟量能背离。
        """
        if yesterday_close <= 0 or volume_avg_20d <= 0:
            return None

        gap_percent = (open_price - yesterday_close) / yesterday_close
        volume_ratio = volume_first_30m / volume_avg_20d

        # 1. 向下跳空：过度恐慌买入反弹 (Fade The Gap)
        # 条件: Gap < -2% 且 开盘量并未出现恐慌性踩踏 (Volume < 1.5x)
        if gap_percent < -self.gap_threshold and volume_ratio < self.volume_ratio_threshold:
            logger.info(f"[{stock_code}] GAP_FADE triggered: Gap {gap_percent:.2%}, VolRatio {volume_ratio:.2f}")
            return IntradaySignal.create(
                stock_code=stock_code,
                signal_type=IntradaySignalType.GAP_FADE,
                direction=SignalType.LONG,
                priority=Priority.HIGH,
                timestamp=current_time,
                gap_percent=gap_percent,
                volume_ratio=volume_ratio,
                confidence_score=80.0 + abs(gap_percent) * 100,  # 跌越多反弹博弈值越高
                reason=f"低开 {gap_percent:.2%} 时成交量未失控 ({volume_ratio:.2f}x)，博弈日内均值回归买点"
            )

        # 2. 向上跳空假突破：高开诱多 (Fade The Gap)
        # 条件: Gap > 2% 但动能不足 (Volume < 1.5x)，可能是诱多
        if gap_percent > self.gap_threshold and volume_ratio < self.volume_ratio_threshold:
            # 出点或做空预警信号（LONG的反面）
            logger.info(f"[{stock_code}] GAP_FADE (SHORT) triggered: Gap {gap_percent:.2%}, VolRatio {volume_ratio:.2f}")
            return IntradaySignal.create(
                stock_code=stock_code,
                signal_type=IntradaySignalType.GAP_FADE,
                direction=SignalType.SHORT,
                priority=Priority.HIGH,
                timestamp=current_time,
                gap_percent=gap_percent,
                volume_ratio=volume_ratio,
                confidence_score=85.0,
                reason=f"高开 {gap_percent:.2%} 但量缩 ({volume_ratio:.2f}x)，警惕诱多，建议减仓"
            )

        # 3. 向上跳空真突破：强势动量延续 (Breakaway Gap)
        # 条件: Gap > 2% 且巨量换手确认 (Volume > 2.0x)
        if gap_percent > self.gap_threshold and volume_ratio > self.volume_ratio_threshold + 0.5:
            logger.info(f"[{stock_code}] GAP_FOLLOW triggered: Gap {gap_percent:.2%}, VolRatio {volume_ratio:.2f}")
            return IntradaySignal.create(
                stock_code=stock_code,
                signal_type=IntradaySignalType.GAP_FOLLOW,
                direction=SignalType.LONG,
                priority=Priority.HIGH,
                timestamp=current_time,
                gap_percent=gap_percent,
                volume_ratio=volume_ratio,
                confidence_score=90.0,
                reason=f"跳空放量突破 (Gap {gap_percent:.2%}, Vol {volume_ratio:.2f}x)，追击强势动量"
            )

        return None

    def analyze_momentum_transmission(
        self,
        follower_code: str,
        current_time: datetime,
        leader_code: str,
        leader_intraday_return: float,
        follower_intraday_return: float,
        cluster_id: int
    ) -> IntradaySignal | None:
        """
        利用盘前 30-60 分钟推导同集群内领头羊向跟风小弟的动能传导。

        Args:
            leader_intraday_return: 领头羊当日早盘实时收益 （要求暴拉）
            follower_intraday_return: 跟风股收益（要求还未跟上）
        """
        # 规则：若龙头暴涨超 3%，但小弟还在平盘或跌（< 1%），产生补涨预期
        if leader_intraday_return > 0.03 and follower_intraday_return < 0.01:
            diff = leader_intraday_return - follower_intraday_return
            logger.info(f"[{follower_code}] MOMENTUM_LAG triggered via {leader_code}. Diff: {diff:.2%}")
            return IntradaySignal.create(
                stock_code=follower_code,
                signal_type=IntradaySignalType.MOMENTUM_LAG,
                direction=SignalType.LONG,
                priority=Priority.HIGH,
                timestamp=current_time,
                intraday_return=follower_intraday_return,
                leader_stock=leader_code,
                cluster_id=cluster_id,
                confidence_score=min(100.0, 70.0 + diff * 500), # 价差越大得分越高
                reason=f"同 Cluster 龙头 {leader_code} 已拉升 {leader_intraday_return:.2%}，该股滞涨存在传导空间"
            )

        return None
