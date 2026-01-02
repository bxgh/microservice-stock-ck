from datetime import datetime, timedelta
from typing import Optional
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from gsd_shared.utils.calendar_service import CalendarService

class TradingDayTrigger(BaseTrigger):
    """
    交易日触发器
    
    包装一个底层触发器 (如 CronTrigger)，但只在交易日触发。
    如果底层触发器计算出的时间是非交易日，则跳过该日，寻找下一个交易日的触发点。
    """
    
    def __init__(self, trigger: BaseTrigger, calendar_service: Optional[CalendarService] = None):
        self.trigger = trigger
        self.calendar_service = calendar_service or CalendarService()
        
    def get_next_fire_time(self, previous_fire_time: Optional[datetime], now: datetime) -> Optional[datetime]:
        next_fire_time = previous_fire_time
        import logging
        logger = logging.getLogger(__name__)
        
        # Limit loop to avoid infinite search (e.g. if no trading days for a year)
        # 365 days should be enough to find a trading day
        for _ in range(365):
            # Calculate next candidate
            # If we have a 'next_fire_time' from previous iteration (which was rejected),
            # we simply use it as the base 'previous_fire_time' for the trigger.
            # Standard CronTrigger behavior should return the *next* fire time > previous_fire_time.
            # To be absolutely safe against trigger implementation (inclusive start), we add a tiny delta.
             
            if next_fire_time:
                 search_base = next_fire_time + timedelta(microseconds=1)
            else:
                 search_base = now
            
            # Force forward search by acting as if 'now' is the search_base
            # This prevents the trigger from looking back at the real 'now' (Jan 2nd) and finding pending jobs (Jan 3rd) repeatedly.
            next_fire_time = self.trigger.get_next_fire_time(search_base, search_base)
            
            if next_fire_time is None:
                return None
            
            # Check if trading day
            if self.calendar_service.is_trading_day(next_fire_time.date()):
                logger.info(f"✅ Found trading day fire time: {next_fire_time}")
                return next_fire_time
            
            logger.info(f"⏭️ Skipping non-trading day: {next_fire_time.date()}")
            
            # Jump to next day 00:00
            # We use the computed next_fire_time (e.g. Jan 3rd 15:05) to determine "today".
            # We want to start searching from "tomorrow" (Jan 4th 00:00).
            next_day_start = (next_fire_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Update search_base for next iteration
            next_fire_time = next_day_start

            
        logger.error("🚨 TradingDayTrigger could not find a trading day within 365 days!")
        return None

    def __str__(self):
        return f"TradingDayTrigger[{self.trigger}]"
        
    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.trigger})>"
