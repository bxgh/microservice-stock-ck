
import asyncio
import os
import logging
from datetime import datetime
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core.sync_service import KLineSyncService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def verify_integrity():
    service = KLineSyncService()
    try:
        await service.initialize()
        
        logger.info("开始数据完整性校验...")
        
        # 1. Check MySQL Total Count and Max Date
        mysql_count = 0
        mysql_max_date = None
        async with service.mysql_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT COUNT(*) FROM stock_kline_daily")
                mysql_count = (await cur.fetchone())[0]
                
                await cur.execute("SELECT MAX(trade_date) FROM stock_kline_daily")
                mysql_max_date = (await cur.fetchone())[0]
        
        logger.info(f"MySQL Source: count={mysql_count:,}, max_date={mysql_max_date}")

        # 2. Check ClickHouse Total Count and Max Date
        ch_count = 0
        ch_max_date = None
        async with service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT COUNT(*) FROM stock_kline_daily")
                ch_count = (await cur.fetchone())[0]
                
                await cur.execute("SELECT MAX(trade_date) FROM stock_kline_daily")
                ch_max_date = (await cur.fetchone())[0]

        logger.info(f"ClickHouse Target: count={ch_count:,}, max_date={ch_max_date}")
        
        # 3. Comparison
        diff = mysql_count - ch_count
        if diff == 0:
            logger.info("✅ 数据总量一致")
        elif diff > 0:
             logger.warning(f"⚠️  ClickHouse 少于 MySQL {diff:,} 条数据 (可能是尚未同步或被去重)")
        else:
             logger.warning(f"⚠️  ClickHouse 多于 MySQL {abs(diff):,} 条数据 (可能是重复数据)")
             
        if str(mysql_max_date) == str(ch_max_date):
            logger.info(f"✅ 最新交易日期一致: {mysql_max_date}")
        else:
            logger.warning(f"⚠️  最新交易日期不一致: MySQL={mysql_max_date}, CH={ch_max_date}")

    except Exception as e:
        logger.error(f"校验失败: {e}")
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(verify_integrity())
