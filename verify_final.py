import asyncio
import aiomysql
import json
import logging
from datetime import datetime
import os

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 36301))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "alwaysup@888")
MYSQL_DB = "alwaysup"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def final_verification():
    """最终综合验证测试"""
    pool = await aiomysql.create_pool(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, db=MYSQL_DB, autocommit=True)
    
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Test 1: stock_data_supplement with list parameters (Shard 1)
                logger.info("Test 1: 定向补充任务 (Shard 1, 列表参数)")
                params1 = {
                    "stocks": ["000001", "600519"],  # 列表格式
                    "date": datetime.now().strftime("%Y%m%d"),
                    "data_types": ["tick"],
                    "shard_id": 1
                }
                
                sql = "INSERT INTO task_commands (task_id, params, status) VALUES (%s, %s, %s)"
                await cur.execute(sql, ("stock_data_supplement", json.dumps(params1), "PENDING"))
                test1_id = cur.lastrowid
                logger.info(f"已插入 Test #1 (ID {test1_id}): 验证列表参数序列化")
                
                # Test 2: stock_data_supplement with single stock (Shard 2)
                logger.info("Test 2: 定向补充任务 (Shard 2, 单股票)")
                params2 = {
                    "stocks": ["000002"],
                    "date": datetime.now().strftime("%Y%m%d"),
                    "data_types": ["tick"],
                    "shard_id": 2,
                    "priority": "high"
                }
                await cur.execute(sql, ("stock_data_supplement", json.dumps(params2), "PENDING"))
                test2_id = cur.lastrowid
                logger.info(f"已插入 Test #2 (ID {test2_id}): 验证 Shard 2 执行")
                
                # Test 3: repair_tick with shard_id (Shard 0)
                logger.info("Test 3: 全量修复任务 (Shard 0)")
                params3 = {
                    "date": datetime.now().strftime("%Y%m%d"),
                    "shard_id": 0
                }
                await cur.execute(sql, ("repair_tick", json.dumps(params3), "PENDING"))
                test3_id = cur.lastrowid
                logger.info(f"已插入 Test #3 (ID {test3_id}): 验证 shard_id 忽略")
                
                # Monitor results
                logger.info("\n等待 90 秒监控执行结果...")
                start_time = datetime.now()
                tests = {test1_id: "Test1_Shard1", test2_id: "Test2_Shard2", test3_id: "Test3_Shard0"}
                results = {}
                
                while (datetime.now() - start_time).seconds < 90 and len(results) < len(tests):
                    await asyncio.sleep(3)
                    
                    for tid, name in tests.items():
                        if tid in results: continue
                        
                        await cur.execute("SELECT status, result FROM task_commands WHERE id=%s", (tid,))
                        row = await cur.fetchone()
                        if not row: continue
                        
                        status, result = row
                        if status in ['DONE', 'FAILED']:
                            results[tid] = (name, status, result)
                            if status == 'DONE':
                                logger.info(f"✅ {name} (ID {tid}): SUCCESS")
                            else:
                                logger.error(f"❌ {name} (ID {tid}): FAILED - {result[:200]}")
                
                # Summary
                logger.info("\n=== 测试汇总 ===")
                success_count = sum(1 for _, status, _ in results.values() if status == 'DONE')
                logger.info(f"通过: {success_count}/{len(tests)}")
                
                if success_count == len(tests):
                    logger.info("🎉 所有测试通过！分布式补采系统已就绪。")
                else:
                    logger.warning("⚠️ 部分测试失败，请检查日志。")
                    
    finally:
        pool.close()
        await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(final_verification())
