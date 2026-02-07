"""
Backtest结果模型

用于存储策略回测结果和性能指标
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """
    回测结果数据结构

    包含策略回测的所有关键指标
    """
    strategy_name: str              # 策略名称
    period_start: datetime          # 回测开始时间 (CST)
    period_end: datetime            # 回测结束时间 (CST)
    initial_capital: float          # 初始资金
    final_capital: float            # 最终资金
    total_return: float             # 总收益率 (0.15 = 15%)
    max_drawdown: float             # 最大回撤 (0.08 = 8%)
    sharpe_ratio: float             # 夏普比率
    total_signals: int              # 总信号数
    win_rate: float | None = None           # 胜率 (可选)
    total_trades: int | None = None         # 总交易次数 (可选)
    detailed_results: dict[str, Any] | None = field(default_factory=dict)  # 详细结果

    def __post_init__(self):
        """初始化后验证"""
        # 验证时区
        if self.period_start.tzinfo is None:
            raise ValueError("period_start必须包含时区信息")
        if self.period_end.tzinfo is None:
            raise ValueError("period_end必须包含时区信息")

        # 验证时间顺序
        if self.period_start >= self.period_end:
            raise ValueError("period_start必须早于period_end")

        # 验证资金
        if self.initial_capital <= 0:
            raise ValueError(f"initial_capital必须大于0: {self.initial_capital}")

        # 验证数值范围
        if self.total_signals < 0:
            raise ValueError(f"total_signals不能为负: {self.total_signals}")

        logger.info(f"BacktestResult created for {self.strategy_name}: "
                   f"return={self.total_return:.2%}, sharpe={self.sharpe_ratio:.2f}")

    def get_profit(self) -> float:
        """
        获取盈利金额

        Returns:
            盈利金额
        """
        return self.final_capital - self.initial_capital

    def get_annual_return(self) -> float:
        """
        计算年化收益率

        Returns:
            年化收益率
        """
        days = (self.period_end - self.period_start).days
        if days <= 0:
            return 0.0

        years = days / 365.0
        if years <= 0:
            return self.total_return

        # 年化收益率 = (1 + 总收益率)^(1/年数) - 1
        annual_return = (1 + self.total_return) ** (1 / years) - 1
        return annual_return

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典

        Returns:
            字典表示
        """
        return {
            'strategy_name': self.strategy_name,
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'profit': self.get_profit(),
            'total_return': self.total_return,
            'annual_return': self.get_annual_return(),
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'total_signals': self.total_signals,
            'win_rate': self.win_rate,
            'total_trades': self.total_trades,
            'detailed_results': self.detailed_results
        }

    def summary(self) -> str:
        """
        生成摘要字符串

        Returns:
            摘要文本
        """
        return f"""
回测结果摘要
{'='*50}
策略名称: {self.strategy_name}
回测期间: {self.period_start.date()} 至 {self.period_end.date()}
初始资金: ¥{self.initial_capital:,.2f}
最终资金: ¥{self.final_capital:,.2f}
盈亏金额: ¥{self.get_profit():,.2f}
总收益率: {self.total_return:.2%}
年化收益: {self.get_annual_return():.2%}
最大回撤: {self.max_drawdown:.2%}
夏普比率: {self.sharpe_ratio:.2f}
交易信号: {self.total_signals}次
{'='*50}
        """.strip()
