import asyncio
import aiomysql
import sys
import os
import json
from unittest.mock import AsyncMock
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings
from gsd_agent.core import SmartDecisionEngine
from gsd_agent.schemas import DiagnosisResult
from core.flow_controller import FlowController

async def verify_diagnosis():
    # 0. Mock Agent Engine
    mock_agent = AsyncMock(spec=SmartDecisionEngine)
    # Define a mock result: RETRY_IMMEDIATE
    mock_agent.run.return_value = DiagnosisResult(
        root_cause="Transient network error (Connection Reset)",
        action_type="RETRY_IMMEDIATE",
        confidence_score=0.99,
        risk_level=1,
        reasoning="Simple transient failure, safe to retry."
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
    
    print("\n>>> Running Diagnosis & Recovery...")
    await controller._monitor_running_commands()
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            print("\n>>> Task Commands Status (Latest 3):")
            # Should see 1 FAILED (AI_DIAGNOSED) and 1 NEW PENDING (cloned for retry)
            await cursor.execute("SELECT id, step_id, status, result FROM alwaysup.task_commands ORDER BY id DESC LIMIT 3")
            cmds = await cursor.fetchall()
            for c in cmds:
                print(c)

    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(verify_diagnosis())
