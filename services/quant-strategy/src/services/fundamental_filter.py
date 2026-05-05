"""
基本面过滤服务

封装基本面风控规则，用于长线股票池筛选
"""

import logging
from typing import Any

from datetime import datetime
import pytz

from core.risk import RiskManager
from models.signal import Signal, SignalType, Priority
from config.settings import settings
from strategies.rules_fundamental import (
    CashflowQualityRule,
    FinancialFraudRule,
    GoodwillRiskRule,
    PledgeRiskRule,
    RegulatoryBlacklistRule,
    STRiskRule,
)

logger = logging.getLogger(__name__)


class FundamentalFilter:
    """基本面过滤器 - 用于长线选股的财务风控"""

    def __init__(
        self,
        goodwill_threshold: float = 0.3,
        pledge_threshold: float = 0.5,
        cashflow_threshold: float = 0.5,
        cash_threshold: float = 0.2,
        debt_threshold: float = 0.2
    ):
        """
        初始化基本面过滤器

        Args:
            goodwill_threshold: 商誉占净资产比例阈值
            pledge_threshold: 大股东质押率阈值
            cashflow_threshold: 收现比阈值
            cash_threshold: 货币资金占总资产比例阈值
            debt_threshold: 有息负债占总资产比例阈值
        """
        self._risk_manager = RiskManager()
        self._risk_manager.clear_rules()

        # 添加基本面风控规则
        self._risk_manager.add_rule(STRiskRule())
        self._risk_manager.add_rule(RegulatoryBlacklistRule())
        self._risk_manager.add_rule(GoodwillRiskRule(goodwill_threshold))
        self._risk_manager.add_rule(PledgeRiskRule(pledge_threshold))
        self._risk_manager.add_rule(CashflowQualityRule(cashflow_threshold))
        self._risk_manager.add_rule(FinancialFraudRule(cash_threshold, debt_threshold))

        logger.info("FundamentalFilter initialized with 6 risk rules")

    async def filter_stocks(self, stock_codes: list[str]) -> dict[str, Any]:
        """
        批量过滤股票

        Args:
            stock_codes: 股票代码列表

        Returns:
            {
                'passed': [通过的股票代码],
                'rejected': [被拒绝的股票代码],
                'rejection_reasons': {股票代码: [拒绝原因列表]}
            }
        """
        passed = []
        rejected = []
        rejection_reasons = {}

        for code in stock_codes:
            dummy_signal = Signal(
                stock_code=code,
                signal_type=SignalType.LONG,
                priority=Priority.MEDIUM,
                timestamp=datetime.now(pytz.timezone(settings.timezone)),
                strategy_name="fundamental_filter_service",
                reason="fundamental_filter",
                score=50.0,
                price=10.0
            )

            is_valid = await self._risk_manager.validate(dummy_signal)

            if is_valid:
                passed.append(code)
            else:
                rejected.append(code)
                # TODO: 收集具体的拒绝原因
                rejection_reasons[code] = ["Failed fundamental risk check"]

        logger.info(
            f"Fundamental filter completed: {len(passed)} passed, {len(rejected)} rejected "
            f"out of {len(stock_codes)} stocks"
        )

        return {
            'passed': passed,
            'rejected': rejected,
            'rejection_reasons': rejection_reasons
        }
