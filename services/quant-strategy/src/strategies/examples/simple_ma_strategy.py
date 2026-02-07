"""
Simple MA (Moving Average) Strategy Example

简单均线策略 - 用于验证BaseStrategy设计
使用真实数据，无Mock
"""
import logging
from typing import Any

import pandas as pd

from core.strategy_registry import strategy
from models.signal import Priority, Signal, SignalType
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


@strategy("SimpleMA")
class SimpleMAStrategy(BaseStrategy):
    """
    简单均线策略

    逻辑:
    - 当前价格 > 5日均线 → 做多信号
    - 当前价格 < 5日均线 → 做空信号

    使用真实数据进行测试
    """

    def __init__(self, name: str = "SimpleMA", parameters: dict[str, Any] = None):
        default_params = {
            'short_window': 5,    # 短期均线
            'long_window': 10,    # 长期均线
            'threshold': 0.01     # 信号阈值 (1%)
        }

        if parameters:
            default_params.update(parameters)

        super().__init__(name, default_params)

    async def initialize(self) -> None:
        """初始化策略"""
        # 验证参数
        if not self.validate_parameters():
            raise ValueError("Invalid parameters")

        await self._mark_initialized()
        logger.info(f"MA Strategy initialized with params: {self.parameters}")

    def validate_parameters(self) -> bool:
        """
        验证参数

        Returns:
            True if valid

        Raises:
            ValueError: 参数无效
        """
        short = self.parameters.get('short_window', 0)
        long = self.parameters.get('long_window', 0)

        if short <= 0 or long <= 0:
            raise ValueError("均线周期必须大于0")

        if short >= long:
            raise ValueError(f"短期均线({short})必须小于长期均线({long})")

        return True

    async def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """
        生成交易信号

        Args:
            data: 实时行情数据 (从StockDataProvider获取)

        Returns:
            Signal列表
        """
        signals = []

        try:
            # 数据验证
            if data.empty:
                logger.warning("Empty data received")
                return signals

            # 确保有price列
            if 'price' not in data.columns:
                logger.error("Missing 'price' column in data")
                return signals

            # 处理每只股票
            for _, row in data.iterrows():
                try:
                    stock_code = row.get('code', row.get('stock_code', 'UNKNOWN'))
                    current_price = float(row['price'])

                    # 简化逻辑: 基于价格和阈值生成信号
                    # (实际MA计算需要历史数据，这里仅作示例)
                    threshold = self.parameters['threshold']

                    # 模拟MA逻辑: 如果价格变化超过阈值
                    change_pct = row.get('change_pct', 0)

                    if abs(change_pct) >= threshold * 100:
                        signal_type = SignalType.LONG if change_pct > 0 else SignalType.SHORT
                        priority = Priority.HIGH if abs(change_pct) > 2 else Priority.MEDIUM

                        signal = Signal.create(
                            stock_code=str(stock_code),
                            signal_type=signal_type,
                            priority=priority,
                            strategy_name=self.name,
                            reason=f"价格变动 {change_pct:.2f}% 超过阈值",
                            score=min(abs(change_pct) * 10, 100),
                            price=current_price,
                            metadata={
                                'change_pct': change_pct,
                                'threshold': threshold
                            }
                        )

                        signals.append(signal)
                        logger.info(f"Signal generated for {stock_code}: {signal_type.value}")

                except Exception as e:
                    logger.error(f"Error processing row: {e}")
                    continue

            logger.info(f"Generated {len(signals)} signals")
            return signals

        except Exception as e:
            logger.exception(f"Error in generate_signals: {e}")
            return []
