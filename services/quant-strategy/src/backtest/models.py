"""回测数据模型

本模块定义了回测引擎使用的配置和结果数据结构。
使用Pydantic进行数据验证和序列化。
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class BacktestConfig(BaseModel):
    """回测配置"""
    
    initial_capital: float = Field(
        default=100000.0,
        gt=0,
        description="初始资金"
    )
    
    commission_rate: float = Field(
        default=0.0003,
        ge=0,
        le=0.1,
        description="交易佣金费率 (默认万三)"
    )
    
    stamp_duty: float = Field(
        default=0.001,
        ge=0,
        le=0.1,
        description="印花税 (默认千一, 仅卖出收取)"
    )
    
    use_next_open: bool = Field(
        default=False,
        description="是否使用次日开盘价成交 (True=次日开盘, False=当日收盘)"
    )
    
    risk_free_rate: float = Field(
        default=0.03,
        ge=0,
        description="无风险利率 (默认3%)"
    )

class TradeRecord(BaseModel):
    """交易记录"""
    stock_code: str
    direction: str  # BUY/SELL
    price: float
    volume: int
    amount: float
    commission: float
    tax: float
    timestamp: datetime
    strategy_id: str
    reason: str
    realized_pnl: Optional[float] = None  # 平仓时的实现盈亏

class PerformanceMetrics(BaseModel):
    """绩效指标"""
    total_return: float = Field(description="总收益率")
    annualized_return: float = Field(description="年化收益率")
    max_drawdown: float = Field(description="最大回撤")
    sharpe_ratio: float = Field(description="夏普比率")
    volatility: float = Field(description="波动率")
    win_rate: float = Field(description="胜率")
    total_trades: int = Field(description="总交易次数")
    winning_trades: int = Field(description="盈利次数")
    losing_trades: int = Field(description="亏损次数")

class BacktestResult(BaseModel):
    """回测结果"""
    strategy_id: str
    stock_code: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    metrics: PerformanceMetrics
    equity_curve: List[Dict[str, Any]] = Field(description="净值曲线: [{'date': ..., 'value': ...}]")
    trades: List[TradeRecord]
    config: BacktestConfig
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
