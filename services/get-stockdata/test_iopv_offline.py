import asyncio
import logging
import aiohttp
from datetime import datetime
import asynch

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.collector.components.writer import ClickHouseWriter
from src.core.collector.components.snapshot_worker import SnapshotWorker

logging.basicConfig(level=logging.INFO)

async def main():
    mootdx_api_url = "http://127.0.0.1:8003"
    
    # 使用 41 节点代理库
    clickhouse_pool = await asynch.create_pool(
        host='127.0.0.1', 
        port=9000,
        database='stock_data',
        user='default',
        password='',
        minsize=1, maxsize=5
    )
    
    # 因为 add_snapshots 固定向 _local 写入，这里不用改 table_name
    writer = ClickHouseWriter(clickhouse_pool)
    
    connector = aiohttp.TCPConnector(limit=10)
    http_session = aiohttp.ClientSession(connector=connector)
    
    # 510300: 华泰柏瑞沪深300ETF (汇金重点), 159915: 创业板ETF
    stock_pool = ["sh510300", "sz159915", "sh600519"] 
    sem = asyncio.Semaphore(5)
    
    worker = SnapshotWorker(
        http_session=http_session,
        writer=writer,
        stock_pool=stock_pool,
        semaphore=sem,
        mootdx_api_url=mootdx_api_url,
        batch_size=len(stock_pool),
        interval=3.0,
        circuit_breaker=None,
        max_retries=1
    )
    
    today = datetime.now().date()
    snapshot_time = datetime.now()
    
    print("\n[1] 正在直接调用 mootdx-api 获取快照 (Bypassing Trading Time)...")
    rows = await worker._fetch_snapshot_batch(0, stock_pool, today, snapshot_time)
    print(f"[2] 成功获取并解包 Tuple 行数: {len(rows)}")
    
    for r in rows:
        # Tuple 的第 3 维是 code，第 6 维是 price，最后一维(-1)是我们要检查的 iopv
        print(f"    -> 股票: {r[2]:<8} | 价格: {r[5]:<8} | 解析出的 IOPV: {r[-1]}")
        
    print("\n[3] 正在调用 Writer 执行底层 ClickHouse 异步批量写入...")
    await writer.add_snapshots(rows)
    print("[4] 写入动作完成！")
    
    print("\n[5] 正在去 ClickHouse 读取刚刚落盘的数据进行核查...")
    async with clickhouse_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 无论 shard 路由到哪里，分布式表都能查全
            await cursor.execute("SELECT stock_code, current_price, iopv, created_at FROM snapshot_data WHERE stock_code IN ('510300', '159915') ORDER BY created_at DESC LIMIT 2")
            res = await cursor.fetchall()
            for row in res:
                print(f"    -> DB 核实: 股票={row[0]}, DB价格={row[1]}, DB包含IOPV={row[2]}")
                
    await http_session.close()
    clickhouse_pool.close()
    await clickhouse_pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
