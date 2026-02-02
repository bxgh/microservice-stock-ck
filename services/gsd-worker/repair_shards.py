
import asyncio
import os
import sys
import logging
from datetime import datetime
import pytz

# 修复路径，确保能加载 core 和 gsd_shared
sys.path.append(os.path.join(os.getcwd(), 'src'))
sys.path.append(os.path.join(os.getcwd(), 'libs/gsd-shared'))

from core.tick_sync_service import TickSyncService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RepairGaps")
CST = pytz.timezone('Asia/Shanghai')

async def repair(shard_index: int, shard_total: int, target_date: str):
    logger.info(f"🚀 Starting surgical repair for Shard {shard_index}/{shard_total} on {target_date}")
    
    current_date_str = datetime.now(CST).strftime("%Y%m%d")
    is_today = (target_date == current_date_str)
    
    service = TickSyncService()
    await service.initialize()
    
    # --- Monkey Patch Fetcher for "Today" Handling ---
    if is_today:
        original_fetch = service.fetcher.fetch
        async def patched_fetch(stock_code, trade_date=None, start=0):
            # For today, we pass None to the inner fetch logic to avoid ?date=today empty results
            return await original_fetch(stock_code, None, start)
        service.fetcher.fetch = patched_fetch
        logger.info("🐒 Applied Today-Date monkey patch to Fetcher")
    # --------------------------------------------------
    
    try:
        # 1. 获取该分片的股票名单
        stocks = await service.fetch_sync_list(
            scope="all",
            shard_index=shard_index,
            shard_total=shard_total,
            trade_date=target_date
        )
        
        logger.info(f"📦 Total stocks in Shard {shard_index} for repair: {len(stocks)}")
        
        if not stocks:
            logger.warning("⚠️ No stocks found for this shard. Check Redis/MySQL connectivity.")
            return

        # 2. 执行批量同步
        results = await service.sync_stocks(
            stock_codes=stocks,
            trade_date=target_date,
            concurrency=30, # 稍微降低并发以确保稳定性
            force=True,
            idempotent=False
        )
        
        logger.info(f"✅ Repair for Shard {shard_index} finished: {results}")
        
    finally:
        await service.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 repair_shards.py <shard_index> <target_date>")
        sys.exit(1)
        
    idx = int(sys.argv[1])
    date = sys.argv[2]
    
    asyncio.run(repair(idx, 3, date))
