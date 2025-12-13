"""Signal数据模型单元测试

测试Signal的数据验证、序列化和反序列化功能。
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from strategies.signal import Signal


class TestSignalCreation:
    """测试Signal对象创建"""
    
    def test_create_valid_signal(self):
        """测试创建有效的信号"""
        signal = Signal(
            stock_code="600519",
            direction="BUY",
            strength=0.85,
            price=1800.50,
            reason="MACD金叉且成交量放大",
            strategy_id="macd_001"
        )
        
        assert signal.stock_code == "600519"
        assert signal.direction == "BUY"
        assert signal.strength == 0.85
        assert signal.price == 1800.50
        assert signal.reason == "MACD金叉且成交量放大"
        assert signal.strategy_id == "macd_001"
        assert isinstance(signal.timestamp, datetime)
        assert signal.metadata == {}
    
    def test_create_signal_with_metadata(self):
        """测试创建带扩展字段的信号"""
        signal = Signal(
            stock_code="000001",
            direction="SELL",
            strength=0.6,
            price=15.20,
            reason="均线死叉",
            strategy_id="ma_strategy",
            metadata={
                "stop_loss": 16.0,
                "position_size": 0.1,
                "risk_score": 0.3
            }
        )
        
        assert signal.metadata["stop_loss"] == 16.0
        assert signal.metadata["position_size"] == 0.1
        assert signal.metadata["risk_score"] == 0.3


class TestSignalValidation:
    """测试Signal数据验证"""
    
    def test_invalid_stock_code_empty(self):
        """测试空股票代码"""
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                stock_code="",
                direction="BUY",
                strength=0.5,
                price=100.0,
                reason="test",
                strategy_id="test"
            )
        
        assert "股票代码不能为空" in str(exc_info.value)
    
    def test_invalid_stock_code_length(self):
        """测试股票代码长度错误"""
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                stock_code="60051",  # 只有5位
                direction="BUY",
                strength=0.5,
                price=100.0,
                reason="test",
                strategy_id="test"
            )
        
        assert "必须是6位" in str(exc_info.value)
    
    def test_invalid_direction(self):
        """测试无效的交易方向"""
        with pytest.raises(ValidationError):
            Signal(
                stock_code="600519",
                direction="INVALID",
                strength=0.5,
                price=100.0,
                reason="test",
                strategy_id="test"
            )
    
    def test_strength_boundary_values(self):
        """测试信号强度边界值"""
        # 最小值
        signal1 = Signal(
            stock_code="600519",
            direction="HOLD",
            strength=0.0,
            price=100.0,
            reason="test",
            strategy_id="test"
        )
        assert signal1.strength == 0.0
        
        # 最大值  
        signal2 = Signal(
            stock_code="600519",
            direction="BUY",
            strength=1.0,
            price=100.0,
            reason="test",
            strategy_id="test"
        )
        assert signal2.strength == 1.0
