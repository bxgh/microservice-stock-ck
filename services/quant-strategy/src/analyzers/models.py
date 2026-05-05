from dataclasses import dataclass
from typing import Optional
from decimal import Decimal

@dataclass
class VolatilityMetrics:
    annual_volatility: float    # 年化波动率
    avg_amplitude: float        # 日均振幅
    max_amplitude: float        # 极限振幅

@dataclass
class DrawdownMetrics:
    first_peak_price: float     # 首波峰值价格
    first_peak_date: str        # 首波峰值日期
    first_trough_price: float   # 首波谷底价格
    first_trough_date: str      # 首波谷底日期
    drawdown_pct: float         # 回撤幅度 (0-1)
    peak_days: int              # 上市到峰值天数
    trough_days: int            # 峰值到谷底天数

@dataclass
class MultiplesMetrics:
    first_wave_gain: float      # 首波涨幅 (相对于首日开盘)
    high_to_issue: float        # 历史最高/发行价倍数
    current_to_issue: float     # 当前价格/发行价倍数
    issue_price: Optional[Decimal] = None

@dataclass
class BetaMetrics:
    beta: float                 # Beta 系数
    category: str               # 进攻型/跟随型/独立型

@dataclass
class LiquidityMetrics:
    avg_turnover: float         # 平均换手率
    recent_turnover: float      # 近期换手率 (5日)
    decay_rate: float           # 换手衰减率 (近期/均值)
    hot_days: int               # 换手率 > 10% 的天数

@dataclass
class RecoveryMetrics:
    is_recovered: bool          # 是否已收复首波高点
    recovery_days: Optional[int] = None # 从谷底到复苏的天数
