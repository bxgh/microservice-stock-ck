import asyncio
import logging
import json
import os
import signal
from datetime import datetime
from src.core.intraday_tick_service import IntradayTickService

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("IntradayTickWorker")

class IntradayTickWorker:
    def __init__(self):
        self.service = IntradayTickService()
        self.is_running = False
        self.queue_name = "queue:intraday_tick_tasks"

    async def start(self):
        logger.info("🚀 Starting Intraday Tick Worker...")
        await self.service.initialize()
        self.is_running = True
        
        # 限制并发拉取数，防止打挂 TDX 服务器和本地句柄
        sem = asyncio.Semaphore(10)
        
        async def wrapped_process(task):
            async with sem:
                await self.service.process_task(task)

        while self.is_running:
            try:
                result = await self.service.redis.brpop(self.queue_name, timeout=5)
                
                if result:
                    _, payload = result
                    task = json.loads(payload)
                    asyncio.create_task(wrapped_process(task))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(5)
                
        await self.stop()

    async def stop(self):
        logger.info("🛑 Stopping Intraday Tick Worker...")
        self.is_running = False
        await self.service.close()

async def main():
    worker = IntradayTickWorker()
    
    # Handle signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))
        
    try:
        await worker.start()
    except Exception as e:
        logger.critical(f"FATAL: Worker crashed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
