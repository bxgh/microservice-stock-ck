"""
基本面风控规则

用于长线资产配置的财务风险过滤
"""

import logging
from typing import Any

from adapters.stock_data_provider import data_provider
from core.risk import RiskRule
from models.signal import Signal
from services.stock_pool.blacklist_service import blacklist_service

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

            pledge_ratio = indicators.major_shareholder_pledge_ratio or 0.0
            if pledge_ratio > self._threshold:
                logger.info(
                    f"Risk Check Failed: {signal.stock_code} pledge ratio "
                    f"{pledge_ratio:.2%} > threshold {self._threshold:.2%}"
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
            if indicators.net_profit > 0 and indicators.cash_to_profit_ratio < self._threshold:
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


class STRiskRule(RiskRule):
    """ST/退市风险规则 - 一票否决ST和*ST股票"""

    @property
    def name(self) -> str:
        return "STRiskRule"

    async def check(self, signal: Signal, context: dict[str, Any] = None) -> bool:
        """检查股票名称是否带有 ST 或 *ST"""
        try:
            stock_info = await data_provider.get_stock_info(signal.stock_code)
            if not stock_info:
                logger.warning(f"Failed to get stock info for {signal.stock_code}")
                # 默认宽容，获取不到信息时暂时放行，或者根据严格程度返回False
                # 但稳健起见，获取不到基础信息建议放行(防误杀)或拦截。这里选拦截。
                return False

            name = stock_info.get("name", "").upper()
            if "ST" in name:
                logger.info(f"Risk Check Failed: {signal.stock_code} ({name}) is marked as ST/*ST")
                return False

            return True
        except Exception as e:
            logger.error(f"Error in STRiskRule for {signal.stock_code}: {e}", exc_info=True)
            return False


class RegulatoryBlacklistRule(RiskRule):
    """监管黑名单拦截规则 - 与BlacklistService联动"""

    @property
    def name(self) -> str:
        return "RegulatoryBlacklistRule"

    async def check(self, signal: Signal, context: dict[str, Any] = None) -> bool:
        """检查股票是否在动态/永久黑名单中"""
        try:
            is_blacklisted, reason, _ = await blacklist_service.is_blacklisted(signal.stock_code)
            if is_blacklisted:
                logger.info(f"Risk Check Failed: {signal.stock_code} is blacklisted (Reason: {reason})")
                return False

            return True
        except Exception as e:
            logger.error(f"Error in RegulatoryBlacklistRule for {signal.stock_code}: {e}", exc_info=True)
            return False
