import pytest
from datetime import date, time
from src.core.scheduling.calendar_service import CalendarService, MarketType

def test_trading_day_basic():
    service = CalendarService()
    
    # 2025-11-28 是周五 (假设是正常工作日)
    assert service.is_trading_day(date(2025, 11, 28)) == True

    # 2025-11-29 是周六
    assert service.is_trading_day(date(2025, 11, 29)) == False
    
    # 2025-11-30 是周日
    assert service.is_trading_day(date(2025, 11, 30)) == False

def test_holidays():
    service = CalendarService()
    
    # 2024-05-01 劳动节 (周三)
    assert service.is_trading_day(date(2024, 5, 1)) == False
    
    # 2024-02-09 除夕 (周五) - 假设休市
    # chinese_calendar 可能会标记为假期
    assert service.is_trading_day(date(2024, 2, 9)) == False

def test_adjusted_workdays():
    service = CalendarService()
    
    # 2024-02-04 是周日，但是春节调休上班
    # A股规则：周末即使调休上班，也休市
    assert service.is_trading_day(date(2024, 2, 4)) == False
    
    # 2024-04-28 是周日，劳动节调休上班
    assert service.is_trading_day(date(2024, 4, 28)) == False

def test_business_hours():
    service = CalendarService()
    
    # 上午交易
    assert service.is_business_hours(time(9, 30)) == True
    assert service.is_business_hours(time(11, 29)) == True
    
    # 集合竞价
    assert service.is_business_hours(time(9, 15)) == True
    
    # 午休
    assert service.is_business_hours(time(12, 0)) == False
    
    # 下午交易
    assert service.is_business_hours(time(13, 0)) == True
    assert service.is_business_hours(time(15, 0)) == True
    
    # 收盘
    assert service.is_business_hours(time(15, 30)) == False

def test_get_next_trading_day_boundaries():
    service = CalendarService()
    
    # 跨月测试: 2025-01-31 (周五) -> 2025-02-05 (周三)
    # 2025年春节假期: 1月28日-2月4日
    next_day = service.get_next_trading_day(date(2025, 1, 31))
    assert next_day.month == 2
    assert next_day.day == 5
    
    # 跨年测试: 2025-12-31 (周三) -> 2026-01-02 (周五)
    # 假设 1月1日元旦放假
    next_day = service.get_next_trading_day(date(2025, 12, 31))
    assert next_day.year == 2026
    assert next_day.month == 1
    # 具体几号取决于2026元旦放假安排，只要跨年成功即可

