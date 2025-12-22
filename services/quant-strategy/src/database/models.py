"""
Database models for Quant Strategy Service

SQLAlchemy async models for persisting strategy configurations and signals.
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class StrategyConfig(Base):
    """策略配置表"""
    __tablename__ = 'strategy_configs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_name = Column(String(100), nullable=False, unique=True, index=True)
    strategy_type = Column(String(50), nullable=False)  # e.g., 'OFI', 'SmartMoney'

    # Configuration parameters stored as JSON
    parameters = Column(JSON, nullable=False, default={})

    # Status
    enabled = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # Metadata
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<StrategyConfig(name={self.strategy_name}, type={self.strategy_type})>"


class StrategySignal(Base):
    """策略信号表"""
    __tablename__ = 'strategy_signals'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Signal identification
    strategy_name = Column(String(100), nullable=False, index=True)
    stock_code = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)  # LONG, SHORT, CLOSE, HOLD
    priority = Column(String(20), nullable=False)  # HIGH, MEDIUM, LOW

    # Signal data
    price = Column(Float, nullable=True)
    score = Column(Float, default=0.0, nullable=False)
    reason = Column(Text, nullable=True)
    signal_metadata = Column(JSON, nullable=True, default={})  # Renamed from 'metadata' (reserved)

    # Timestamps
    generated_time = Column(DateTime, default=datetime.now, nullable=False, index=True)

    def __repr__(self):
        return f"<StrategySignal(strategy={self.strategy_name}, stock={self.stock_code}, type={self.signal_type})>"


class BacktestRecord(Base):
    """回测记录表"""
    __tablename__ = 'backtest_records'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Backtest identification
    strategy_name = Column(String(100), nullable=False, index=True)
    backtest_name = Column(String(200), nullable=True)

    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Capital
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=False)

    # Performance metrics
    total_return = Column(Float, nullable=False)
    max_drawdown = Column(Float, nullable=False)
    sharpe_ratio = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    total_signals = Column(Integer, default=0, nullable=False)

    # Detailed results stored as JSON
    detailed_results = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f"<BacktestRecord(strategy={self.strategy_name}, return={self.total_return:.2%})>"
