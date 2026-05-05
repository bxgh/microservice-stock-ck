import asyncio
import aiomysql
import os

async def query_failures():
    conn = await aiomysql.connect(
        host="127.0.0.1", port=36301,
        user="root", password="alwaysup@888",
        db="alwaysup"
    )
    async with conn.cursor() as cur:
        await cur.execute("SELECT id, task_id, params, status, result FROM task_commands WHERE id IN (36, 37, 38, 40, 41, 42)")
        print(f"{'ID':<5} {'TASK':<15} {'SHARD':<6} {'STATUS':<10} {'RESULT'}")
        print("-" * 100)
        async for row in cur:
            id_val, task, params, status, result = row
            shard = "?"
            if '"shard_id": 0' in params: shard = "0"
            elif '"shard_id": 1' in params: shard = "1" 
            elif '"shard_id": 2' in params: shard = "2"
            
            # Truncate result for display
            res_short = (result[:80] + '...') if result and len(result) > 80 else result
            print(f"{id_val:<5} {task:<15} {shard:<6} {status:<10} {res_short}")
    conn.close()

if __name__ == "__main__":
    asyncio.run(query_failures())
