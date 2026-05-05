import asyncio
import aiomysql
import asynch
from config.settings import settings
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mysql_timeout():
    logger.info(f"Testing MySQL connection timeout (expected: {settings.db_connect_timeout}s)...")
    start = time.time()
    try:
        # Use a non-routable IP to force a timeout
        pool = await aiomysql.create_pool(
            host='192.168.255.255', 
            port=3306,
            user='root',
            password='password',
            db='test',
            connect_timeout=settings.db_connect_timeout
        )
        await pool.acquire()
        logger.error("❌ MySQL: Connected unexpectedly!")
    except Exception as e:
        duration = time.time() - start
        logger.info(f"✅ MySQL: Caught expected exception: {e}")
        logger.info(f"✅ MySQL: Time taken: {duration:.2f}s")
        if abs(duration - settings.db_connect_timeout) < 2:
            logger.info("✅ MySQL: Timeout is within expected range.")
        else:
            logger.warning(f"⚠️ MySQL: Timeout duration {duration:.2f}s deviates from expected {settings.db_connect_timeout}s")

async def test_clickhouse_timeout():
    logger.info(f"Testing ClickHouse connection timeout (expected: {settings.db_connect_timeout}s)...")
    start = time.time()
    try:
        # Wrap the whole creation in asyncio.wait_for to ensure it doesn't hang
        pool = await asyncio.wait_for(
            asynch.create_pool(
                host='192.168.255.255',
                port=9000,
                user='default',
                password='',
                database='default',
                connect_timeout=settings.db_connect_timeout,
                send_receive_timeout=settings.db_io_timeout,
                sync_request_timeout=settings.db_io_timeout
            ),
            timeout=settings.db_connect_timeout + 2 # Give a small buffer
        )
        async with pool.acquire() as conn:
             pass
        logger.error("❌ ClickHouse: Connected unexpectedly!")
    except Exception as e:
        duration = time.time() - start
        logger.info(f"✅ ClickHouse: Caught expected exception: {e}")
        logger.info(f"✅ ClickHouse: Time taken: {duration:.2f}s")
        if abs(duration - settings.db_connect_timeout) < 2:
            logger.info("✅ ClickHouse: Timeout is within expected range.")
        else:
            logger.warning(f"⚠️ ClickHouse: Timeout duration {duration:.2f}s deviates from expected {settings.db_connect_timeout}s")

if __name__ == "__main__":
    asyncio.run(test_mysql_timeout())
    asyncio.run(test_clickhouse_timeout())
