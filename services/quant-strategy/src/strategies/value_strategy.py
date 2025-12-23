"""
价值策略示例

基于 PE/PB 估值和 ROE 盈利能力的选股策略。
用于测试 ScannerEngine 流程。
"""
import logging
from typing import Any

from strategies.base_strategy import (
    BaseStrategy,
    MarketRegime,
    StrategyResult,
    Timeframe,
)

logger = logging.getLogger(__name__)


class ValueStrategy(BaseStrategy):
    """
    低估值价值策略
    
    选股逻辑:
    - PE < 阈值 (默认 20)
    - PB < 阈值 (默认 3)
    - ROE > 阈值 (默认 10%)
    """
    
    def __init__(self, parameters: dict[str, Any] | None = None):
        params = parameters or {}
        super().__init__(name="价值策略", parameters=params)
        
        # 策略参数
        self.pe_threshold = params.get("pe_threshold", 20.0)
        self.pb_threshold = params.get("pb_threshold", 3.0)
        self.roe_threshold = params.get("roe_threshold", 10.0)
    
    @property
    def strategy_id(self) -> str:
        return "value"
    
    @property
    def timeframe(self) -> Timeframe:
        return Timeframe.DAILY
    
    @property
    def preferred_regime(self) -> list[MarketRegime]:
        # 价值策略在熊市和震荡市表现更好
        return [MarketRegime.BEAR, MarketRegime.RANGE]
    
    async def evaluate(self, stock_code: str, data: dict[str, Any]) -> StrategyResult:
        """
        评估股票是否符合价值策略
        
        Args:
            stock_code: 股票代码
            data: 包含 financials, valuation 等数据
        """
        score = 0.0
        reasons = []
        details = {}
        
        # 获取估值数据
        valuation = data.get("valuation", {})
        pe = valuation.get("pe_ttm") or valuation.get("pe", 999)
        pb = valuation.get("pb_ratio") or valuation.get("pb", 999)
        
        # 获取财务数据
        financials = data.get("financials", {})
        roe = financials.get("roe", 0)
        
        details["pe"] = pe
        details["pb"] = pb
        details["roe"] = roe
        
        # PE 评分 (权重 40%)
        if pe < self.pe_threshold:
            pe_score = min((self.pe_threshold - pe) / self.pe_threshold * 100, 40)
            score += pe_score
            reasons.append(f"PE={pe:.1f}<{self.pe_threshold}")
        
        # PB 评分 (权重 30%)
        if pb < self.pb_threshold:
            pb_score = min((self.pb_threshold - pb) / self.pb_threshold * 100, 30)
            score += pb_score
            reasons.append(f"PB={pb:.1f}<{self.pb_threshold}")
        
        # ROE 评分 (权重 30%)
        if roe > self.roe_threshold:
            roe_score = min((roe - self.roe_threshold) / 10 * 30, 30)
            score += roe_score
            reasons.append(f"ROE={roe:.1f}%>{self.roe_threshold}%")
        
        # 判断是否通过
        passed = score >= 60  # 60分及格
        
        return StrategyResult(
            strategy_id=self.strategy_id,
            stock_code=stock_code,
            score=round(score, 2),
            passed=passed,
            reason=", ".join(reasons) if reasons else "不符合价值标准",
            details=details
        )
