from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, DateTime, JSON, Index, Text
from sqlalchemy.orm import Mapped, mapped_column
from ..core.database import Base

class CCIRecord(Base):
    """CCI 指标记录表"""
    __tablename__ = "CCI_records"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), index=True, comment="股票/指数代码")
    trade_date: Mapped[datetime] = mapped_column(DateTime, index=True, comment="交易日期")
    
    # 核心指标
    cci_value: Mapped[float] = mapped_column(Float, comment="CCI 计算值")
    rho_value: Mapped[float] = mapped_column(Float, comment="横截面相关性 Rho")
    var_value: Mapped[float] = mapped_column(Float, comment="方差 Var")
    
    # 状态
    layer: Mapped[str] = mapped_column(String(10), index=True, comment="监测层级 L1-L6")
    is_critical: Mapped[bool] = mapped_column(default=False, comment="是否处于临界状态")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("ix_CCI_records_code_date", "stock_code", "trade_date", unique=True),
    )

class CCIAlert(Base):
    """CCI 预警记录表"""
    __tablename__ = "CCI_alerts"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(20), index=True)
    alert_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    
    layer: Mapped[str] = mapped_column(String(10))
    alert_type: Mapped[str] = mapped_column(String(20), comment="预警类型: CRITICAL_SLOWING, DISLOCATION")
    severity: Mapped[str] = mapped_column(String(10), default="INFO")
    
    message: Mapped[str] = mapped_column(Text)
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class CCIDislocation(Base):
    """CCI 层级错位记录表"""
    __tablename__ = "CCI_dislocations"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trade_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    
    base_layer: Mapped[str] = mapped_column(String(10), comment="基准层级")
    target_layer: Mapped[str] = mapped_column(String(10), comment="对比层级")
    
    dislocation_score: Mapped[float] = mapped_column(Float, comment="错位分值")
    direction: Mapped[int] = mapped_column(comment="方向: 1(向上错位), -1(向下错位)")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
