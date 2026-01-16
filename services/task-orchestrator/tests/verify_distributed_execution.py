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

async def verify_distribution():
    pool = await aiomysql.create_pool(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, db=MYSQL_DB, autocommit=True)
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                tasks = [(1, "Server 58", ["600519"]), (2, "Server 111", ["000002"])]
                inserted_ids = {}
                for shard_id, label, stocks in tasks:
                    params = {"stocks": stocks, "date": datetime.now().strftime("%Y%m%d"), "data_types": ["tick"], "shard_id": shard_id, "priority": "normal"}
                    sql = "INSERT INTO task_commands (task_id, params, status) VALUES (%s, %s, %s)"
                    await cur.execute(sql, ("stock_data_supplement", json.dumps(params), "PENDING"))
                    inserted_ids[shard_id] = cur.lastrowid
                    logger.info(f"Deployed Probe Task #{cur.lastrowid} for {label}")

                logger.info("Waiting for pollers (60s)...")
                start_time = datetime.now()
                completed = set()
                while len(completed) < len(tasks) and (datetime.now() - start_time).seconds < 60:
                    await asyncio.sleep(2)
                    for shard_id, cmd_id in inserted_ids.items():
                        if shard_id in completed: continue
                        await cur.execute("SELECT status, result FROM task_commands WHERE id=%s", (cmd_id,))
                        row = await cur.fetchone()
                        if row and row[0] in ['RUNNING', 'DONE', 'FAILED']:
                            logger.info(f"Task #{cmd_id} (Shard {shard_id}) status -> {row[0]}")
                            if row[0] in ['DONE', 'FAILED']:
                                logger.info(f"Result: {row[1]}")
                                completed.add(shard_id)

                if len(completed) == len(tasks): logger.info("✅ SUCCESS: All remote pollers responsive!")
                else: logger.error(f"❌ TIMEOUT: Missing {set(inserted_ids.keys()) - completed}")
    finally:
        pool.close()
        await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(verify_distribution())
