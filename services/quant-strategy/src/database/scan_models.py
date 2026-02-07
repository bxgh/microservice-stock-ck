"""
扫描任务数据库模型

存储每日扫描任务和策略匹配结果。
"""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database.models import Base


class ScanJobModel(Base):
    """扫描任务表"""
    __tablename__ = "scan_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), unique=True, nullable=False, index=True)
    scan_date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")
    total_stocks = Column(Integer, default=0)
    processed_stocks = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    matches = relationship("StrategyMatchModel", back_populates="scan_job", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "scan_date": self.scan_date.isoformat() if self.scan_date else None,
            "status": self.status,
            "total_stocks": self.total_stocks,
            "processed_stocks": self.processed_stocks,
            "progress_percent": (self.processed_stocks / self.total_stocks * 100) if self.total_stocks > 0 else 0,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error_message": self.error_message
        }


class StrategyMatchModel(Base):
    """策略匹配结果表"""
    __tablename__ = "strategy_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_job_id = Column(Integer, ForeignKey("scan_jobs.id"), nullable=False)
    scan_date = Column(Date, nullable=False, index=True)  # 冗余字段便于查询
    stock_code = Column(String(10), nullable=False, index=True)
    strategy_id = Column(String(50), nullable=False, index=True)
    score = Column(Float, default=0.0)
    passed = Column(Boolean, default=False)
    reason = Column(Text, nullable=True)
    details = Column(Text, nullable=True)  # JSON 格式
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    scan_job = relationship("ScanJobModel", back_populates="matches")

    # 复合唯一约束
    __table_args__ = (
        UniqueConstraint('scan_date', 'stock_code', 'strategy_id', name='uq_date_stock_strategy'),
    )

    def to_dict(self) -> dict[str, Any]:
        import json
        return {
            "stock_code": self.stock_code,
            "strategy_id": self.strategy_id,
            "score": self.score,
            "passed": self.passed,
            "reason": self.reason,
            "details": json.loads(self.details) if self.details else {},
            "scan_date": self.scan_date.isoformat() if self.scan_date else None
        }


class ScanErrorModel(Base):
    """扫描错误记录表"""
    __tablename__ = "scan_errors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_job_id = Column(Integer, ForeignKey("scan_jobs.id"), nullable=False)
    stock_code = Column(String(10), nullable=False)
    strategy_id = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stock_code": self.stock_code,
            "strategy_id": self.strategy_id,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
