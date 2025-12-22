"""
基本面风控规则

用于长线资产配置的财务风险过滤
"""

import logging
from typing import Any

from adapters.stock_data_provider import data_provider
from core.risk import RiskRule
from strategies.signal import Signal

logger = logging.getLogger(__name__)


class GoodwillRiskRule(RiskRule):
    """商誉风控规则 - 防止商誉减值雷"""

    def __init__(self, threshold: float = 0.3):
        """
        Args:
            threshold: 商誉占净资产比例阈值 (默认30%)
        """
        self._threshold = threshold

    @property
    def name(self) -> str:
        return "GoodwillRiskRule"

    async def check(self, signal: Signal, context: dict[str, Any] = None) -> bool:
        """检查商誉占净资产比例是否过高"""
        try:
            indicators = await data_provider.get_financial_indicators(signal.stock_code)
            if not indicators:
                logger.warning(f"Failed to get financial indicators for {signal.stock_code}, rejecting by default")
                return False

            if indicators.goodwill_ratio > self._threshold:
                logger.info(
                    f"Risk Check Failed: {signal.stock_code} goodwill ratio "
                    f"{indicators.goodwill_ratio:.2%} > threshold {self._threshold:.2%}"
                )
                return False

            return True
        except Exception as e:
            logger.error(f"Error in GoodwillRiskRule for {signal.stock_code}: {e}", exc_info=True)
            return False


class PledgeRiskRule(RiskRule):
    """质押风控规则 - 防止大股东质押爆仓风险"""

    def __init__(self, threshold: float = 0.5):
        """
        Args:
            threshold: 大股东质押率阈值 (默认50%)
        """
        self._threshold = threshold

    @property
    def name(self) -> str:
        return "PledgeRiskRule"

    async def check(self, signal: Signal, context: dict[str, Any] = None) -> bool:
        """检查大股东质押率是否过高"""
        try:
            indicators = await data_provider.get_financial_indicators(signal.stock_code)
            if not indicators:
                logger.warning(f"Failed to get financial indicators for {signal.stock_code}, rejecting by default")
                return False

            if indicators.major_shareholder_pledge_ratio > self._threshold:
                logger.info(
                    f"Risk Check Failed: {signal.stock_code} pledge ratio "
                    f"{indicators.major_shareholder_pledge_ratio:.2%} > threshold {self._threshold:.2%}"
                )
                return False

            return True
        except Exception as e:
            logger.error(f"Error in PledgeRiskRule for {signal.stock_code}: {e}", exc_info=True)
            return False


class CashflowQualityRule(RiskRule):
    """收现比风控规则 - 防止利润质量差的公司"""

    def __init__(self, threshold: float = 0.5):
        """
        Args:
            threshold: 收现比阈值 (经营现金流/净利润，默认0.5)
        """
        self._threshold = threshold

    @property
    def name(self) -> str:
        return "CashflowQualityRule"

    async def check(self, signal: Signal, context: dict[str, Any] = None) -> bool:
        """检查收现比是否过低 (仅对盈利公司检查)"""
        try:
            indicators = await data_provider.get_financial_indicators(signal.stock_code)
            if not indicators:
                logger.warning(f"Failed to get financial indicators for {signal.stock_code}, rejecting by default")
                return False

            # 只对盈利公司检查收现比
            if indicators.net_profit > 0:
                if indicators.cash_to_profit_ratio < self._threshold:
                    logger.info(
                        f"Risk Check Failed: {signal.stock_code} cash-to-profit ratio "
                        f"{indicators.cash_to_profit_ratio:.2f} < threshold {self._threshold:.2f}"
                    )
                    return False

            return True
        except Exception as e:
            logger.error(f"Error in CashflowQualityRule for {signal.stock_code}: {e}", exc_info=True)
            return False


class FinancialFraudRule(RiskRule):
    """存贷双高规则 - 识别潜在财务造假"""

    def __init__(self, cash_threshold: float = 0.2, debt_threshold: float = 0.2):
        """
        Args:
            cash_threshold: 货币资金占总资产比例阈值 (默认20%)
            debt_threshold: 有息负债占总资产比例阈值 (默认20%)
        """
        self._cash_threshold = cash_threshold
        self._debt_threshold = debt_threshold

    @property
    def name(self) -> str:
        return "FinancialFraudRule"

    async def check(self, signal: Signal, context: dict[str, Any] = None) -> bool:
        """检查是否存在存贷双高特征"""
        try:
            indicators = await data_provider.get_financial_indicators(signal.stock_code)
            if not indicators:
                logger.warning(f"Failed to get financial indicators for {signal.stock_code}, rejecting by default")
                return False

            # 存贷双高：账上有很多钱，同时借了很多钱
            is_dual_high = (
                indicators.cash_ratio > self._cash_threshold and
                indicators.debt_ratio > self._debt_threshold
            )

            if is_dual_high:
                logger.warning(
                    f"Risk Check Failed: {signal.stock_code} shows dual-high pattern "
                    f"(cash ratio: {indicators.cash_ratio:.2%}, debt ratio: {indicators.debt_ratio:.2%})"
                )
                return False

            return True
        except Exception as e:
            logger.error(f"Error in FinancialFraudRule for {signal.stock_code}: {e}", exc_info=True)
            return False
