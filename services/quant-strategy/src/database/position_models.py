"""
Position Pool Database Models

SQLAlchemy async models for managing active holdings (Position Pool).
Includes tracking of entry/exit points, P&L, risk parameters, and liquidity metrics.
"""
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, Integer, String

# Import Base from models to share metadata
from database.models import Base


class PositionStock(Base):
    """
    持仓池 (Position Pool)

    管理当前实际持仓，包含交易详情、盈亏状态和流动性风险指标。
    """
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 基础信息
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    strategy_type = Column(String(20), nullable=False)  # 'long_term' | 'swing'

    # 交易数据
    entry_price = Column(Float, nullable=False)         # 建仓均价
    quantity = Column(Integer, nullable=False)          # 持仓数量 (股)
    entry_date = Column(Date, nullable=False)           # 建仓日期

    # 实时/更新数据
    current_price = Column(Float, nullable=True)        # 最新价格
    current_value = Column(Float, nullable=True)        # 最新市值

    # 盈亏统计
    profit_loss = Column(Float, nullable=True)          # 浮动盈亏 (元)
    profit_loss_pct = Column(Float, nullable=True)      # 浮动盈亏率 (%)

    # 风险控制
    stop_loss = Column(Float, nullable=True)            # 止损价
    take_profit = Column(Float, nullable=True)          # 止盈价
    holding_days = Column(Integer, default=0)           # 持仓天数

    # 流动性风险管理 (Story 5.4 核心要求)
    avg_daily_volume = Column(Float, nullable=True)     # 20日日均成交额 (元)
    liquidity_impact = Column(String(10), default="LOW") # LOW/MEDIUM/HIGH
    liquidation_cost_est = Column(Float, nullable=True) # 预估清算冲击成本 (元)

    # 状态
    status = Column(String(20), default='holding')      # 'holding' | 'closed' | 'partial'

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self):
        return f"<Position({self.code} {self.name}, qty={self.quantity}, pnl={self.profit_loss_pct}%)>"
