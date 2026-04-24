## Epic 6: 调度与推送

### Story 6.1: 每日定时任务 (4h)

```python
# backend/src/cci_monitor/scheduler/main.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ..services.daily_service import DailyService
from ..core.logger import logger

async def main():
    scheduler = AsyncIOScheduler()
    service = DailyService()
    
    # 交易日 17:00 运行
    scheduler.add_job(
        service.run_daily,
        CronTrigger(day_of_week='mon-fri', hour=17, minute=0),
        id='daily_cci_computation',
        max_instances=1,  # 防止重复
    )
    
    # 每小时健康检查
    scheduler.add_job(
        service.health_check,
        CronTrigger(minute=0),
        id='hourly_health_check',
    )
    
    scheduler.start()
    logger.info("Scheduler started")
    
    # 保持运行
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        scheduler.shutdown()
```

### Story 6.2: 多通道推送 (4h)

支持 Server 酱 + SMTP + Bark。**带防骚扰机制**。

```python
# backend/src/cci_monitor/scheduler/notifier.py
class Notifier:
    async def send_alert(self, alert: AlertRecord):
        # 去重检查(24h 内同级别不重复推送)
        if self._is_duplicate(alert):
            return
        
        # 多通道并发推送
        results = await asyncio.gather(
            self._send_server_chan(alert),
            self._send_email(alert),
            return_exceptions=True,
        )
        
        # 至少一个成功即算成功
        if any(not isinstance(r, Exception) for r in results):
            self._record_sent(alert)
```

### Story 6.3: 日报生成 (3h)

---

