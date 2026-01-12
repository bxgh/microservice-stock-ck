import asyncio
import logging
import xxhash
from core.tick_sync_service import TickSyncService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    service = TickSyncService()
    await service.initialize()
    
    # 1. Get full list
    logger.info("Fetching full stock list...")
    stocks = await service.get_all_stocks()
    total = len(stocks)
    logger.info(f"Total stocks fetched: {total}")
    
    if total == 0:
        logger.error("Fetched 0 stocks! Check mootdx-api.")
        await service.close()
        return

    # 2. Simulate Sharding
    shard_counts = {0: 0, 1: 0, 2: 0}
    shard_0_stocks = []
    
    for code in stocks:
        shard = xxhash.xxh64(code).intdigest() % 3
        shard_counts[shard] += 1
        if shard == 0:
            shard_0_stocks.append(code)
            
    logger.info(f"Theoretical Shard Distribution (Total {total}):")
    for s, c in shard_counts.items():
        ratio = c / total * 100
        logger.info(f"  Shard {s}: {c} ({ratio:.2f}%)")
        
    # Check if 648 matches any specific logic (e.g. maybe only one market was fetched?)
    sz_stocks = [c for c in stocks if c.startswith(('00', '30'))]
    sh_stocks = [c for c in stocks if c.startswith(('60', '68'))]
    logger.info(f"Market breakdown: SZ={len(sz_stocks)}, SH={len(sh_stocks)}")
    
    await service.close()

if __name__ == "__main__":
    asyncio.run(main())
