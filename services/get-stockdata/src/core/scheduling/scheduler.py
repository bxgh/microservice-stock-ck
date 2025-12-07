import asyncio
import logging
from datetime import datetime, timedelta, time
from enum import Enum
from typing import Optional, List
from src.core.scheduling.calendar_service import CalendarService
from src.core.stock_pool.manager import StockPoolManager

class SystemState(Enum):
    RUNNING = "RUNNING"   # 正在运行 (交易时段)
    SLEEPING = "SLEEPING" # 休眠中 (非交易时段)
    PAUSED = "PAUSED"     # 暂停 (人工干预)

class AcquisitionScheduler:
    """
    采集任务调度器
    负责控制采集任务的运行、休眠和唤醒
    """
    
    def __init__(self, calendar_service: Optional[CalendarService] = None, config_manager=None):
        self.calendar = calendar_service or CalendarService()
        self.state = SystemState.SLEEPING
        self.logger = logging.getLogger(__name__)
        
        # 股票池管理器
        self.pool_manager = StockPoolManager(config_manager=config_manager)
        self.current_pool: List[str] = []
        
    def should_run_now(self) -> bool:
        """
        判断当前是否应该运行采集任务
        """
        now = datetime.now()
        
        # 1. 检查是否为交易日
        if not self.calendar.is_trading_day(now.date()):
            return False
            
        # 2. 检查是否为交易时段
        # 提前 5 分钟启动，延迟 5 分钟停止，确保覆盖集合竞价和收盘
        current_time = now.time()
        
        # 定义宽限期 (Buffer)
        # 上午: 09:10 - 11:35
        # 下午: 12:55 - 15:10
        
        am_start = time(9, 10)
        am_end = time(11, 35)
        pm_start = time(12, 55)
        pm_end = time(15, 10)
        
        is_am = am_start <= current_time <= am_end
        is_pm = pm_start <= current_time <= pm_end
        
        return is_am or is_pm

    async def wait_for_next_run(self):
        """
        计算并等待直到下一个运行时间点
        """
        now = datetime.now()
        target_time = self._get_next_start_time(now)
        
        wait_seconds = (target_time - now).total_seconds()
        
        if wait_seconds > 0:
            self.state = SystemState.SLEEPING
            self.logger.info(f"😴 System sleeping until {target_time} ({wait_seconds/3600:.2f} hours)")
            print(f"😴 System sleeping until {target_time} ({wait_seconds/3600:.2f} hours)")
            
            # 冷却连接池
            try:
                from ..monitoring.connection_monitor import connection_monitor
                await connection_monitor.cooldown_all()
            except Exception as e:
                self.logger.warning(f"Failed to cooldown connection pools: {e}")
            
            # 真正的 sleep
            await asyncio.sleep(wait_seconds)
            
            self.state = SystemState.RUNNING
            self.logger.info("⏰ Waking up for trading session!")
            print("⏰ Waking up for trading session!")
            
            # 预热连接池
            try:
                from ..monitoring.connection_monitor import connection_monitor
                await connection_monitor.warmup_all()
            except Exception as e:
                self.logger.warning(f"Failed to warmup connection pools: {e}")

    def _get_next_start_time(self, now: datetime) -> datetime:
        """
        计算下一个启动时间
        """
        current_date = now.date()
        current_time = now.time()
        
        # 定义当天的启动时间点
        today_am_start = datetime.combine(current_date, time(9, 10))
        today_pm_start = datetime.combine(current_date, time(12, 55))
        
        # 情况 1: 今天是交易日
        if self.calendar.is_trading_day(current_date):
            # 还没到上午开盘
            if now < today_am_start:
                return today_am_start
            
            # 上午收盘了，还没到下午开盘
            if now > datetime.combine(current_date, time(11, 35)) and now < today_pm_start:
                return today_pm_start
                
        # 其他情况（下午收盘后，或者非交易日），找下一个交易日的上午开盘
        next_day = self.calendar.get_next_trading_day(current_date)
        return datetime.combine(next_day, time(9, 10))
    
    async def initialize(self):
        """
        初始化调度器
        加载股票池等初始化操作
        """
        self.logger.info("🚀 Initializing AcquisitionScheduler...")
        
        try:
            # 加载股票池
            self.current_pool = await self.pool_manager.get_current_pool()
            self.logger.info(f"✅ Stock pool loaded: {len(self.current_pool)} stocks")
            
            if len(self.current_pool) == 0:
                self.logger.warning("⚠️ Stock pool is empty!")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize stock pool: {e}")
            raise
    
    def get_current_pool(self) -> List[str]:
        """
        获取当前股票池
        
        Returns:
            List[str]: 股票代码列表
        """
        return self.current_pool.copy()
    
    async def refresh_pool(self):
        """
        刷新股票池（每日更新时调用）
        """
        self.logger.info("🔄 Refreshing stock pool...")
        try:
            new_pool = await self.pool_manager.get_current_pool()
            if len(new_pool) > 0:
                self.current_pool = new_pool
                self.logger.info(f"✅ Stock pool refreshed: {len(new_pool)} stocks")
            else:
                self.logger.warning("⚠️ Pool refresh returned empty, keeping old pool")
        except Exception as e:
            self.logger.error(f"❌ Failed to refresh pool: {e}")

if __name__ == "__main__":
    # 简单测试
    scheduler = AcquisitionScheduler()
    print(f"Should run now? {scheduler.should_run_now()}")
    
    now = datetime.now()
    next_run = scheduler._get_next_start_time(now)
    print(f"Next run time: {next_run}")
