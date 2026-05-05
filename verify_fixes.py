import asyncio
import aiomysql
import json
import logging
from datetime import datetime
import os

# Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 36301))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "alwaysup@888")
MYSQL_DB = "alwaysup"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def verify_fixes():
    pool = await aiomysql.create_pool(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, db=MYSQL_DB, autocommit=True)
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Use simple stocks that should exist or be skipped quickly
                tasks = [
                    (1, "Server 58 (Shard 1)", ["000001"]), 
                    (2, "Server 111 (Shard 2)", ["000002"])
                ]
                
                inserted_ids = {}
                for shard_id, label, stocks in tasks:
                    # Note: We are deliberately NOT passing extra args manually here to see if Poller adds them
                    # But the task_id 'stock_data_supplement' target command is now fixed to handle unknown args
                    params = {
                        "stocks": stocks, 
                        "date": datetime.now().strftime("%Y%m%d"), 
                        "data_types": ["tick"], 
                        "shard_id": shard_id, 
                        "priority": "high"
                    }
                    sql = "INSERT INTO task_commands (task_id, params, status) VALUES (%s, %s, %s)"
                    await cur.execute(sql, ("stock_data_supplement", json.dumps(params), "PENDING"))
                    inserted_ids[shard_id] = cur.lastrowid
                    logger.info(f"Deployed Final Probe Task #{cur.lastrowid} for {label}")

                logger.info("Waiting for pollers (max 90s)...")
                start_time = datetime.now()
                completed = set()
                
                while len(completed) < len(tasks) and (datetime.now() - start_time).seconds < 90:
                    await asyncio.sleep(3)
                    for shard_id, cmd_id in inserted_ids.items():
                        if shard_id in completed: continue
                        
                        await cur.execute("SELECT status, result FROM task_commands WHERE id=%s", (cmd_id,))
                        row = await cur.fetchone()
                        if not row: continue
                        
                        status, result = row
                        if status in ['RUNNING', 'DONE', 'FAILED']:
                            logger.info(f"Task #{cmd_id} (Shard {shard_id}) status -> {status}")
                            
                            if status == 'DONE':
                                logger.info(f"✅ Shard {shard_id} Success! Result: {result[:100]}...")
                                completed.add(shard_id)
                            elif status == 'FAILED':
                                logger.error(f"❌ Shard {shard_id} Failed! Result: {result}")
                                completed.add(shard_id)
                
                success_count = 0
                for shard_id, cmd_id in inserted_ids.items():
                    if shard_id in completed:
                        # Re-check final status
                        await cur.execute("SELECT status FROM task_commands WHERE id=%s", (cmd_id,))
                        row = await cur.fetchone()
                        if row and row[0] == 'DONE':
                            success_count += 1
                
                if success_count == len(tasks):
                    logger.info("🎉 ALL SYSTEMS GO: Distributed repair is fully functional.")
                else:
                    logger.warning(f"⚠️ Partial success: {success_count}/{len(tasks)} tasks succeeded.")

    finally:
        pool.close()
        await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(verify_fixes())
