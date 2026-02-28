from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from models.signal import Priority, SignalType


class IntradaySignalType(Enum):
    """日内动量与隔夜跳空的特定交易信号类型"""
    GAP_FOLLOW = "GAP_FOLLOW"  # 强势跳空突破，追高动量
    GAP_FADE = "GAP_FADE"      # 过度跳空，博弈日内均值回归
    MOMENTUM_LAG = "MOMENTUM_LAG" # 龙头暴涨引发的板块情绪滞后扩散补涨
    EOD_ALPHA = "EOD_ALPHA"    # 尾盘 (End-of-Day) 套利，博弈次日溢价


@dataclass
class IntradaySignal:
    """
    日内实时的动量交易信号快照。
    与原策略 `Signal` 相比较，附带了日内的上下文数据，
    能够对接分钟级的 T+0 / 券池日推演引擎。
    """
    stock_code: str
    signal_type: IntradaySignalType
    direction: SignalType  # LONG / SHORT (A股通常用空头压降仓位)
    priority: Priority
    timestamp: datetime

    # 日内特征属性
    gap_percent: float = 0.0
    volume_ratio: float = 1.0
    intraday_return: float = 0.0

    # 若有关联的 Leader (例如 MOMENTUM_LAG) 可记录追随关系
    leader_stock: str | None = None
    cluster_id: int | None = None

    # 给定 0.0~100.0 的操作置信度评分
    confidence_score: float = 0.0
    reason: str = ""

    def __post_init__(self):
        """格式与安全校验"""
        if not self.stock_code or len(self.stock_code) != 6:
            raise ValueError(f"stock_code 必须是6位数字，当前: {self.stock_code}")

        if self.gap_percent > 1.0 or self.gap_percent < -1.0:
            # A股单日跳空不可能 > 100% (除权除息日例外，此策略不覆除权处理)
            raise ValueError(f"gap_percent 跳空比例超限: {self.gap_percent}")

    @classmethod
    def create(cls, **kwargs) -> 'IntradaySignal':
        """工厂方法封装创建过程"""
        return cls(**kwargs)
