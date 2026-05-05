import asyncio
import logging
import os
import aiohttp
from datetime import datetime
from asynch import connect
from gsd_shared.tick.fetcher import TickFetcher
from gsd_shared.tick.utils import clean_stock_code

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 环境配置 (从 get-stockdata 的环境或默认值获取)
CH_HOST = os.getenv("CLICKHOUSE_HOST", "microservice-stock-clickhouse")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
CH_USER = os.getenv("CLICKHOUSE_USER", "admin")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "admin123")
API_URL = os.getenv("MOOTDX_SOURCE_URL", "http://mootdx-source:10086")

async def backfill_date(fetcher, conn, stock_code, date_str):
    logger.info(f"🚀 开始回溯 {stock_code} 在 {date_str} 的数据...")
    
    # 抓取数据 (使用 HISTORICAL 模式进行全量线性扫描)
    ticks = await fetcher.fetch(stock_code, trade_date=date_str)
    if not ticks:
        logger.warning(f"⚠️ {date_str} 未抓取到数据")
        return

    logger.info(f"📈 抓取到 {len(ticks)} 条原始数据，开始处理并写入...")

    # 处理数据
    clean_code = clean_stock_code(stock_code)
    is_fund = any(clean_code.startswith(p) for p in ['51', '52', '56', '58', '59', '15', '16', '18'])
    scale = 0.1 if is_fund else 1.0
    
    rows_to_write = []
    for item in ticks:
        price = float(item.get('price', 0)) * scale
        volume = int(item.get('volume', item.get('vol', 0)))
        iopv = float(item.get('iopv', 0)) * scale if item.get('iopv') else None
        time_str = item.get('time', '')
        direction = 1 if item.get('type') == 'B' else (0 if item.get('type') == 'S' else 2)
        num = item.get('num', 0)
        
        rows_to_write.append((
            clean_code, date_str, time_str, price, iopv, volume,
            price * volume, direction, num
        ))

    # 写入 ClickHouse
    async with conn.cursor() as cursor:
        query = """
        INSERT INTO stock_data.tick_data_intraday_local 
        (stock_code, trade_date, tick_time, price, iopv, volume, amount, direction, num) 
        VALUES
        """
        await cursor.execute(query, rows_to_write)
    
    logger.info(f"✅ {date_str} 数据写入完成，共 {len(rows_to_write)} 条")

async def main():
    stock_code = "510300.SH"
    dates = ["2026-04-02", "2026-04-03"]
    
    async with aiohttp.ClientSession() as session:
        fetcher = TickFetcher(session, API_URL, mode=TickFetcher.Mode.HISTORICAL)
        
        conn = await connect(
            host=CH_HOST,
            port=CH_PORT,
            user=CH_USER,
            password=CH_PASSWORD,
            database="stock_data"
        )
        
        try:
            for date in dates:
                await backfill_date(fetcher, conn, stock_code, date)
        finally:
            await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
