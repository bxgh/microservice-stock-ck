"""
Signal数据结构

定义策略生成的交易信号标准格式
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import pytz


class SignalType(str, Enum):
    """信号类型"""
    LONG = "LONG"      # 做多
    SHORT = "SHORT"    # 做空
    CLOSE = "CLOSE"    # 平仓
    HOLD = "HOLD"      # 持有


class Priority(str, Enum):
    """信号优先级"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Signal:
    """
    交易信号数据结构
    
    所有策略生成的信号必须符合此格式
    """
    stock_code: str              # 股票代码
    signal_type: SignalType      # 信号类型
    priority: Priority           # 优先级
    timestamp: datetime          # 信号生成时间 (CST)
    strategy_name: str           # 策略名称
    reason: str                  # 触发原因
    score: float                 # 信号强度 (0-100)
    price: Optional[float] = None           # 触发价格
    metadata: Optional[Dict[str, Any]] = None  # 额外数据
    
    def __post_init__(self):
        """初始化后验证"""
        # 确保timestamp有时区信息
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp必须包含时区信息")
        
        # 验证score范围
        if not 0 <= self.score <= 100:
            raise ValueError(f"score必须在0-100之间，当前: {self.score}")
        
        # 验证stock_code格式
        if not self.stock_code or len(self.stock_code) != 6:
            raise ValueError(f"stock_code必须是6位数字，当前: {self.stock_code}")
        
        # 初始化metadata
        if self.metadata is None:
            self.metadata = {}
    
    @classmethod
    def create(
        cls,
        stock_code: str,
        signal_type: SignalType,
        priority: Priority,
        strategy_name: str,
        reason: str,
        score: float,
        price: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Signal':
        """
        创建Signal实例，自动添加CST时间戳
        
        Args:
            stock_code: 股票代码
            signal_type: 信号类型
            priority: 优先级
            strategy_name: 策略名称
            reason: 触发原因
            score: 信号强度 (0-100)
            price: 触发价格
            metadata: 额外数据
            
        Returns:
            Signal实例
        """
        cst = pytz.timezone('Asia/Shanghai')
        timestamp = datetime.now(cst)
        
        return cls(
            stock_code=stock_code,
            signal_type=signal_type,
            priority=priority,
            timestamp=timestamp,
            strategy_name=strategy_name,
            reason=reason,
            score=score,
            price=price,
            metadata=metadata
        )
    
    def is_valid(self) -> bool:
        """
        验证信号是否有效
        
        Returns:
            True if valid
        """
        try:
            # 基本字段检查
            if not all([
                self.stock_code,
                self.signal_type,
                self.priority,
                self.timestamp,
                self.strategy_name,
                self.reason
            ]):
                return False
            
            # score范围检查
            if not 0 <= self.score <= 100:
                return False
            
            # 时区检查
            if self.timestamp.tzinfo is None:
                return False
            
            return True
            
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"Signal validation failed: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            字典表示
        """
        return {
            'stock_code': self.stock_code,
            'signal_type': self.signal_type.value,
            'priority': self.priority.value,
            'timestamp': self.timestamp.isoformat(),
            'strategy_name': self.strategy_name,
            'reason': self.reason,
            'score': self.score,
            'price': self.price,
            'metadata': self.metadata
        }
