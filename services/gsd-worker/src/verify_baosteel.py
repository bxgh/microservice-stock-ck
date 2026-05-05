import asyncio
import logging
from core.tick_sync_service import TickSyncService
from core.task_logger import TaskLogger

logging.basicConfig(level=logging.INFO)

async def main():
    service = TickSyncService()
    await service.initialize()
    
    code = "600010"
    date = "20260106"
    
    print(f"--- SYNCING {code} on {date} with SMART STRATEGY ---")
    count = await service.sync_stock(code, date)
    print(f"--- RESULT: {count} rows ---")
    
    await service.close()

if __name__ == "__main__":
    asyncio.run(main())
