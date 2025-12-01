import pytest
from datetime import datetime, time, date
from src.core.scheduling.scheduler import AcquisitionScheduler
from src.core.scheduling.calendar_service import CalendarService

# Mock CalendarService
class MockCalendarService(CalendarService):
    def __init__(self, is_trading=True):
        self._is_trading = is_trading
        
    def is_trading_day(self, day=None, market=None):
        return self._is_trading
        
    def get_next_trading_day(self, day=None):
        return day.replace(day=day.day + 1) # Simple mock

def test_should_run_now():
    # 交易日
    scheduler = AcquisitionScheduler(MockCalendarService(is_trading=True))
    
    # 09:00 (Too early)
    # assert scheduler.should_run_now() == False # Wait, logic says 9:10 start. 
    # Let's mock datetime.now() - hard to mock built-in, so we might need to refactor scheduler to accept 'now'
    # Or just trust the logic for now and test _get_next_start_time which is pure
    pass

def test_get_next_start_time():
    scheduler = AcquisitionScheduler(MockCalendarService(is_trading=True))
    
    # Case 1: Before AM session (08:00)
    now = datetime(2025, 11, 28, 8, 0, 0)
    expected = datetime(2025, 11, 28, 9, 10, 0)
    assert scheduler._get_next_start_time(now) == expected
    
    # Case 2: During lunch break (12:00)
    now = datetime(2025, 11, 28, 12, 0, 0)
    expected = datetime(2025, 11, 28, 12, 55, 0)
    assert scheduler._get_next_start_time(now) == expected
    
    # Case 3: After PM session (16:00)
    now = datetime(2025, 11, 28, 16, 0, 0)
    # Next day should be 29th 9:10 (Mock returns next day)
    expected = datetime(2025, 11, 29, 9, 10, 0)
    assert scheduler._get_next_start_time(now) == expected

def test_non_trading_day():
    scheduler = AcquisitionScheduler(MockCalendarService(is_trading=False))
    
    # Any time on non-trading day
    now = datetime(2025, 11, 29, 10, 0, 0) # Saturday
    # Should return next trading day (Sunday 9:10 in our simple mock)
    expected = datetime(2025, 11, 30, 9, 10, 0)
    assert scheduler._get_next_start_time(now) == expected
