"""
策略相关数据模型
"""

from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StrategyType(str, Enum):
    """策略类型枚举"""
    OFI = "ofi"                           # 主动买卖单失衡策略
    SMART_MONEY = "smart_money"           # 大单资金流向追踪
    ORDER_BOOK_PRESSURE = "order_book"    # 盘口深度压力分析
    VWAP = "vwap"                         # 日内VWAP乖离策略
    LIQUIDITY_SHOCK = "liquidity_shock"   # 流动性冲击监控
    CUSTOM = "custom"                     # 自定义策略


class SignalDirection(str, Enum):
    """信号方向"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class Strategy(BaseModel):
    """策略模型"""
    id: str = Field(..., description="策略唯一ID")
    name: str = Field(..., description="策略名称")
    strategy_type: StrategyType = Field(..., description="策略类型")
    description: Optional[str] = Field(None, description="策略描述")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="策略参数")
    stock_pool: List[str] = Field(default_factory=list, description="股票池")
    enabled: bool = Field(True, description="是否启用")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StrategyCreate(BaseModel):
    """创建策略请求模型"""
    name: str = Field(..., description="策略名称")
    strategy_type: StrategyType = Field(..., description="策略类型")
    description: Optional[str] = Field(None, description="策略描述")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="策略参数")
    stock_pool: List[str] = Field(default_factory=list, description="股票池")


class Signal(BaseModel):
    """交易信号模型"""
    id: str = Field(..., description="信号ID")
    strategy_id: str = Field(..., description="策略ID")
    stock_code: str = Field(..., description="股票代码")
    direction: SignalDirection = Field(..., description="信号方向")
    strength: float = Field(..., ge=0.0, le=1.0, description="信号强度 (0-1)")
    price: float = Field(..., description="触发价格")
    volume: Optional[int] = Field(None, description="建议交易量")
    reason: Optional[str] = Field(None, description="信号触发原因")
    timestamp: datetime = Field(default_factory=datetime.now, description="信号生成时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加信息")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BacktestRequest(BaseModel):
    """回测请求模型"""
    start_date: date = Field(..., description="回测开始日期")
    end_date: date = Field(..., description="回测结束日期")
    initial_capital: float = Field(1000000.0, description="初始资金")
    commission_rate: float = Field(0.0003, description="佣金费率")
    slippage: float = Field(0.001, description="滑点")

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class BacktestResult(BaseModel):
    """回测结果模型"""
    strategy_id: str = Field(..., description="策略ID")
    start_date: date = Field(..., description="回测开始日期")
    end_date: date = Field(..., description="回测结束日期")
    total_return: float = Field(..., description="总收益率")
    annual_return: float = Field(..., description="年化收益率")
    max_drawdown: float = Field(..., description="最大回撤")
    sharpe_ratio: float = Field(..., description="夏普比率")
    win_rate: float = Field(..., description="胜率")
    total_trades: int = Field(..., description="总交易次数")
    status: str = Field(..., description="回测状态")
    message: Optional[str] = Field(None, description="状态消息")

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }


# OFI策略专用参数模型
class OFIParameters(BaseModel):
    """OFI策略参数"""
    window_seconds: int = Field(60, description="滑动窗口秒数")
    buy_threshold: float = Field(2.0, description="买入阈值 (标准差倍数)")
    sell_threshold: float = Field(-2.0, description="卖出阈值 (标准差倍数)")


# Smart Money策略专用参数模型
class SmartMoneyParameters(BaseModel):
    """Smart Money策略参数"""
    large_order_percentile: float = Field(0.95, description="大单分位数阈值")
    small_order_percentile: float = Field(0.25, description="小单分位数阈值")
    lookback_days: int = Field(5, description="历史回溯天数")


# Order Book Pressure策略专用参数模型
class OrderBookParameters(BaseModel):
    """Order Book Pressure策略参数"""
    depth_levels: int = Field(5, description="盘口深度档位")
    weights: List[float] = Field([5, 4, 3, 2, 1], description="各档位权重")
    pressure_threshold: float = Field(0.3, description="压力阈值")


# VWAP策略专用参数模型
class VWAPParameters(BaseModel):
    """VWAP策略参数"""
    std_multiplier: float = Field(2.0, description="标准差倍数")
    oversold_threshold: float = Field(-3.0, description="超卖阈值")
    overbought_threshold: float = Field(3.0, description="超买阈值")


# Liquidity Shock策略专用参数模型
class LiquidityShockParameters(BaseModel):
    """Liquidity Shock策略参数"""
    impact_threshold: float = Field(0.001, description="冲击成本阈值")
    tps_spike_multiplier: float = Field(2.0, description="TPS激增倍数")
