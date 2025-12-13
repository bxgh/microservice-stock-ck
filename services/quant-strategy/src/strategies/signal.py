"""交易信号标准数据结构

本模块定义了量化策略生成的交易信号的标准格式。
使用Pydantic进行数据验证和序列化。
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Literal, Optional
from datetime import datetime


class Signal(BaseModel):
    """交易信号标准数据结构
    
    所有策略生成的信号必须符合此数据结构。
    使用Pydantic进行自动数据验证和类型检查。
    
    Attributes:
        stock_code: 股票代码，6位数字，如 '600519'
        direction: 交易方向，可选值: 'BUY', 'SELL', 'HOLD'
        strength: 信号强度，范围 0.0-1.0，1.0表示最强信号
        price: 目标价格，必须大于0
        timestamp: 信号生成时间，默认为当前时间
        reason: 信号生成原因，用于可解释性和回溯分析
        strategy_id: 生成此信号的策略标识符
        metadata: 扩展字段，可存储止损价、止盈价、仓位等自定义数据
    
    Example:
        >>> signal = Signal(
        ...     stock_code="600519",
        ...     direction="BUY",
        ...     strength=0.85,
        ...     price=1800.50,
        ...     reason="MACD金叉且成交量放大",
        ...     strategy_id="macd_strategy_001",
        ...     metadata={"stop_loss": 1750.0, "position_size": 0.1}
        ... )
    """
    
    stock_code: str = Field(
        ...,
        description="股票代码，6位数字"
    )
    
    direction: Literal["BUY", "SELL", "HOLD"] = Field(
        ...,
        description="交易方向: BUY-买入, SELL-卖出, HOLD-持有"
    )
    
    strength: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="信号强度，范围0-1，1表示最强"
    )
    
    price: float = Field(
        ...,
        gt=0,
        description="目标价格，必须大于0"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="信号生成时间"
    )
    
    reason: str = Field(
        ...,
        min_length=1,
        description="信号生成原因，用于可解释性"
    )
    
    strategy_id: str = Field(
        ...,
        min_length=1,
        description="策略标识符"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="扩展字段，可存储止损价、止盈价、仓位等"
    )
    
    @validator('stock_code')
    def validate_stock_code(cls, v: str) -> str:
        """验证股票代码格式
        
        Args:
            v: 股票代码字符串
            
        Returns:
            验证通过的股票代码
            
        Raises:
            ValueError: 股票代码格式错误
        """
        if not v:
            raise ValueError("股票代码不能为空")
        
        if len(v) != 6:
            raise ValueError(f"股票代码必须是6位，当前长度: {len(v)}")
        
        if not v.isdigit():
            raise ValueError(f"股票代码必须是纯数字，当前值: {v}")
        
        return v
    
    @validator('reason')
    def validate_reason(cls, v: str) -> str:
        """验证信号原因不为空
        
        Args:
            v: 信号原因字符串
            
        Returns:
            验证通过的原因
            
        Raises:
            ValueError: 原因为空
        """
        if not v or not v.strip():
            raise ValueError("信号原因不能为空")
        return v.strip()
    
    class Config:
        """Pydantic配置"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            信号的字典表示
        """
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Signal':
        """从字典创建Signal对象
        
        Args:
            data: 信号数据字典
            
        Returns:
            Signal对象
            
        Raises:
            ValidationError: 数据验证失败
        """
        return cls(**data)
