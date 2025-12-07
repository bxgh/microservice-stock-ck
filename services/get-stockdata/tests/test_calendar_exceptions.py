import pytest
from datetime import date, datetime, time
from src.core.scheduling.calendar_service import CalendarService

def test_is_trading_day_invalid_inputs():
    service = CalendarService()
    
    # 测试非法类型
    with pytest.raises(ValueError) as excinfo:
        service.is_trading_day(123) # int is invalid
    assert "Invalid date type" in str(excinfo.value)
    
    # 测试非法字符串格式
    with pytest.raises(ValueError):
        service.is_trading_day("2025/11/28") # Wrong format

def test_is_trading_day_flexible_inputs():
    service = CalendarService()
    
    # 测试字符串输入
    assert service.is_trading_day("2025-11-28") == True
    
    # 测试datetime输入
    dt = datetime(2025, 11, 28, 10, 0, 0)
    assert service.is_trading_day(dt) == True

def test_is_business_hours_invalid_inputs():
    service = CalendarService()
    
    # 测试非法类型
    with pytest.raises(ValueError):
        service.is_business_hours(123)
    
    # 测试非法字符串格式
    with pytest.raises(ValueError):
        service.is_business_hours("25:00")

def test_is_business_hours_flexible_inputs():
    service = CalendarService()
    
    # 测试字符串输入 (HH:MM)
    assert service.is_business_hours("09:30") == True
    assert service.is_business_hours("12:00") == False
    
    # 测试字符串输入 (HH:MM:SS)
    assert service.is_business_hours("14:00:00") == True
    
    # 测试datetime输入
    dt = datetime(2025, 11, 28, 10, 0, 0)
    assert service.is_business_hours(dt) == True

def test_get_next_trading_day_invalid_inputs():
    service = CalendarService()
    
    # 测试非法类型
    with pytest.raises(ValueError):
        service.get_next_trading_day(123)
    
    # 测试非法字符串格式
    with pytest.raises(ValueError):
        service.get_next_trading_day("11/28/2025")

def test_get_next_trading_day_flexible_inputs():
    service = CalendarService()
    
    # 测试字符串输入
    next_day = service.get_next_trading_day("2025-01-31")
    assert next_day.year == 2025
    assert next_day.month == 2
    
    # 测试datetime输入
    dt = datetime(2025, 1, 31, 10, 0, 0)
    next_day = service.get_next_trading_day(dt)
    assert next_day.month == 2
