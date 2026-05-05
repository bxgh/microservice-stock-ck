import asyncio
import aiomysql
import sys
import os
import json
import uuid
from unittest.mock import AsyncMock
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings
from gsd_agent.core import SmartDecisionEngine
from gsd_agent.schemas import DiagnosisResult
from core.flow_controller import FlowController

async def final_test():
    # 0. Mock Agent Engine
    mock_agent = AsyncMock(spec=SmartDecisionEngine)
    mock_agent.run.return_value = DiagnosisResult(
        root_cause="Mocked Connection Reset",
        action_type="RETRY_IMMEDIATE",
        confidence_score=0.99,
        risk_level=1,
        reasoning="Test retry logic."
    )
    
    pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE,
        minsize=1,
        maxsize=5
    )

    controller = FlowController(pool, None, mock_agent)
    
    # 1. Trigger Run
    run_id = str(uuid.uuid4())
    print(f"🚀 Triggering run {run_id}...")
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO alwaysup.workflow_runs (run_id, workflow_id, status, context) VALUES (%s, %s, %s, %s)",
                (run_id, "distributed_tick_sync_4.0", "RUNNING", json.dumps({"target_date": "20260125"}))
            )
            await conn.commit()

    # 2. Advance (Emit Step 1)
    print(">>> Advancing (Emitting Step 1)...")
    await controller._process_active_runs()
    
    # 3. Fail Step 1 manually
    print(">>> Failing Step 1 manually...")
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "UPDATE alwaysup.task_commands SET status='FAILED', output_context=%s, result='Error: Conn Reset' WHERE run_id=%s AND step_id='fetch_stock_list'",
                (json.dumps({'error_logs': 'Connection reset at 12:00'}), run_id)
            )
            await conn.commit()

    # 4. AI Diagnosis Loop
    print(">>> Running AI Diagnosis Loop...")
    await controller._monitor_running_commands()
    
    # 5. Verify Results
    print("\n>>> Final Result Inspection:")
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT id, step_id, status, result FROM alwaysup.task_commands WHERE run_id=%s ORDER BY id ASC", (run_id,))
            cmds = await cursor.fetchall()
            for c in cmds:
                res_str = (c['result'] or "")[:100]
                print(f"ID: {c['id']}, Step: {c['step_id']}, Status: {c['status']}, Result: {res_str}")
            
            if len(cmds) >= 2 and any(c['status'] == 'PENDING' for c in cmds[1:]):
                print("\n✅ SUCCESS: AI Diagnosis triggered and created a retry command!")
            else:
                print("\n❌ FAILURE: AI Diagnosis or retry command creation failed.")

    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(final_test())
