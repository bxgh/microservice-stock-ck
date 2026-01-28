from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from typing import Literal, Optional, Dict, Any

class AgentConfig(BaseModel):
    """Configuration for the Agent Engine"""
    provider: Literal["openai", "deepseek", "groq", "siliconflow"] = "deepseek"
    model_name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.1
    timeout: int = 30
    fallback_enabled: bool = True

class DiagnosisResult(BaseModel):
    """Result schema for Ops Diagnosis"""
    model_config = ConfigDict(populate_by_name=True)

    root_cause: str = Field(
        ..., 
        validation_alias=AliasChoices("root_cause", "rootCause"),
        description="Analysis of the root cause of the error"
    )
    action_type: Literal["RETRY_IMMEDIATE", "RETRY_WITH_PROXY", "SKIP", "ALERT_ADMIN"] = Field(
        ..., 
        validation_alias=AliasChoices("action_type", "actionType"),
        description="Recommended action"
    )
    confidence_score: float = Field(
        ..., 
        ge=0.0, le=1.0, 
        validation_alias=AliasChoices("confidence_score", "confidenceScore"),
        description="Confidence level of this decision"
    )
    risk_level: int = Field(
        ..., 
        ge=1, le=10, 
        validation_alias=AliasChoices("risk_level", "riskLevel"),
        description="Risk level (1=Low, 10=Critical)"
    )
    reasoning: str = Field(
        ..., 
        validation_alias=AliasChoices("reasoning", "reasoning"),
        description="Brief reasoning behind the decision"
    )
