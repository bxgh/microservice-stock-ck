from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class DQRule(str, Enum):
    INTEGRITY = "integrity"
    CONTINUITY = "continuity"
    SUSPENSION = "suspension"
    NETWORK = "network"

class DQSeverity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"

class DQStatus(str, Enum):
    OPEN = "OPEN"
    FIXED = "FIXED"
    IGNORED = "IGNORED"

class DQFinding(BaseModel):
    ts_code: str
    trade_date: str
    rule_id: DQRule
    severity: DQSeverity = DQSeverity.WARN
    description: str
    found_at: datetime = Field(default_factory=datetime.now)
    status: DQStatus = DQStatus.OPEN

class DQReport(BaseModel):
    inspection_date: str
    start_time: datetime
    end_time: Optional[datetime] = None
    score: float = 0.0
    summary: Dict[str, Any] = {}
    status: str = "COMPLETED"

class DQInspectionResult(BaseModel):
    findings: List[DQFinding]
    report: DQReport
