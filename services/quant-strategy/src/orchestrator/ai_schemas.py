from pydantic import BaseModel, Field
from typing import List, Literal

class FeatureInsight(BaseModel):
    feature_id: str = Field(..., description="指标ID, 如 f1")
    observation: str = Field(..., description="对该指标数值及分位点的客观描述")
    implication: str = Field(..., description="该指标反映的盘口意义（资金意图、流动性状态等）")

class MarketRegime(BaseModel):
    regime_name: str = Field(..., description="盘口状态分类，如：缩量震荡、机构抢筹、知情抛压、主力对倒等")
    confidence: float = Field(..., ge=0.0, le=1.0, description="判决置信度")
    description: str = Field(..., description="状态的详细定性描述")

class StrategyAdvise(BaseModel):
    action: str = Field(..., description="建议动作，如：关注、持币、减仓、博弈")
    reason: str = Field(..., description="核心理由，结合多维特征")

class AIAnalysisResult(BaseModel):
    summary: str = Field(..., description="一段话核心总结")
    insights: List[FeatureInsight] = Field(..., min_items=3, description="关键特征深入解读")
    regime: MarketRegime = Field(..., description="盘口宏观状态判别")
    advice: StrategyAdvise = Field(..., description="专家级策略建议")
