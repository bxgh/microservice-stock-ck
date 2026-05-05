import asyncio
import aiomysql
import sys
import json
from pathlib import Path
from datetime import datetime

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

async def status_report():
    pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE,
        minsize=1,
        maxsize=5
    )

    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            print("\n" + "="*80)
            print(f"📊 AGENTIC WORKFLOW STATUS REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*80)

            # 1. Workflow Runs Summary
            print("\n>>> ACTIVE & RECENT WORKFLOW RUNS:")
            await cursor.execute("SELECT run_id, workflow_id, status, context, start_time FROM alwaysup.workflow_runs ORDER BY start_time DESC LIMIT 5")
            runs = await cursor.fetchall()
            if not runs:
                print("No runs found.")
            for r in runs:
                ctx_summary = json.loads(r['context']) if r['context'] else {}
                print(f"[{r['status']}] Run: {r['run_id'][:8]}... | Workflow: {r['workflow_id']} | Date: {ctx_summary.get('target_date', 'N/A')} | Started: {r['start_time']}")

            # 2. Latest Task Commands
            print("\n>>> LATEST TASK COMMANDS:")
            await cursor.execute("SELECT id, run_id, step_id, status, result FROM alwaysup.task_commands ORDER BY id DESC LIMIT 10")
            cmds = await cursor.fetchall()
            for c in cmds:
                res_info = f" -> {c['result'][:60]}..." if c['result'] else ""
                print(f"ID: {c['id']} | Run: {c['run_id'][:8]}... | Step: {c['step_id']:20} | Status: {c['status']:8}{res_info}")

            # 3. AI Diagnosis Stats
            await cursor.execute("SELECT count(*) as count FROM alwaysup.task_commands WHERE result LIKE 'AI_DIAGNOSED:%'")
            diag_count = (await cursor.fetchone())['count']
            print(f"\n>>> AI RECOVERY STATS:")
            print(f"Total AI Diagnoses: {diag_count}")

            print("\n" + "="*80)

    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(status_report())
