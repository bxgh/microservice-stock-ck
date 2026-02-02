#!/usr/bin/env python3
"""
午盘分笔数据精确修复脚本 (2026-02-02)
逻辑：
1. 从 noon_bad_stocks.json 读取异常股票。
2. 批量物理删除 11:40 之前的早盘脏数据（解决格式冲突）。
3. 调用 TickSyncService 重新同步早盘数据。
"""

import sys
import os
import json
import asyncio
import logging

# 注入路径
sys.path.append("/home/bxgh/microservice-stock/libs/gsd-shared")
sys.path.append("/home/bxgh/microservice-stock/services/gsd-worker/src")

from core.tick_sync_service import TickSyncService

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("RepairNoon")

TARGET_DATE = '20260202'

async def main():
    # 1. 加载待修复清单
    if not os.path.exists('noon_bad_stocks.json'):
        logger.error("❌ 找不到 noon_bad_stocks.json，请先运行审计脚本。")
        return
        
    with open('noon_bad_stocks.json', 'r') as f:
        bad_stocks = json.load(f)
    
    codes = [item['code'] for item in bad_stocks]
    logger.info(f"📦 准备修复 {len(codes)} 只股票的早盘数据")

    # 强制设置环境变量以匹配环境 (必须在初始化 Service 前设置)
    os.environ["CLICKHOUSE_HOST"] = "192.168.151.41"
    os.environ["REDIS_HOST"] = "127.0.0.1"
    os.environ["MOOTDX_API_URL"] = "http://127.0.0.1:8003"

    # 2. 初始化核心服务
    service = TickSyncService()
    await service.initialize()
    
    try:
        # 3. 物理删除早盘数据 (ON CLUSTER)
        # ... (same deletion logic) ...
        async with service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                batch_size = 500
                for i in range(0, len(codes), batch_size):
                    batch = codes[i:i+batch_size]
                    codes_str = ",".join([f"'{c}'" for c in batch])
                    delete_sql = f"""
                        ALTER TABLE stock_data.tick_data_intraday_local ON CLUSTER stock_cluster 
                        DELETE WHERE trade_date = '2026-02-02' 
                        AND tick_time <= '11:40:00'
                        AND stock_code IN ({codes_str})
                    """
                    await cursor.execute(delete_sql)
                    logger.info(f"   -> 已发送批次删除指令 ({min(i+len(batch), len(codes))}/{len(codes)})")

        logger.info("⏳ 等待 ClickHouse Mutation 异步执行 (5秒)...")
        await asyncio.sleep(5)

        # 4. 重新同步数据 (Refill)
        logger.info("📥 Step 2: 正在重新回填早盘分笔数据 (并发=10)...")
        results = await service.sync_stocks(
            stock_codes=codes,
            trade_date=TARGET_DATE,
            concurrency=10,
            force=True,
            idempotent=False
        )
        
        logger.info(f"✅ 修复完成！总计: {results.get('success', 0)} 成功, {results.get('failed', 0)} 失败, {results.get('skipped', 0)} 跳过")
        logger.info(f"📊 累计回填记录数: {results.get('total_records', 0)}")
        
        if results.get('failed_codes'):
            logger.warning(f"❌ 失败列表 (前10): {results['failed_codes'][:10]}")

    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(main())
