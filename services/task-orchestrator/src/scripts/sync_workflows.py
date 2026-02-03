import asyncio
import yaml
import json
import aiomysql
import sys
import os
from pathlib import Path

# Add src to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import settings
from core.workflow_parser import WorkflowParser

async def sync_workflow(file_path: str):
    """Sync a workflow YAML file into MySQL workflow_definitions table"""
    if not os.path.exists(file_path):
        print(f"❌ File {file_path} not found")
        return

    try:
        wf_def = WorkflowParser.parse_file(file_path)
        wf_id = wf_def.id
        wf_name = wf_def.name
        definition_json = wf_def.model_dump_json()

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
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO alwaysup.workflow_definitions (id, name, definition) "
                    "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE name=%s, definition=%s",
                    (wf_id, wf_name, definition_json, wf_name, definition_json)
                )
                await conn.commit()
        
        pool.close()
        await pool.wait_closed()
        print(f"✅ Workflow '{wf_id}' synchronized successfully from {os.path.basename(file_path)}")
    except Exception as e:
        print(f"❌ Failed to sync {file_path}: {e}")

async def main():
    workflows_dir = Path(__file__).parent.parent.parent / "config" / "workflows"
    if not workflows_dir.exists():
        print(f"❌ Workflows directory {workflows_dir} not found")
        return
        
    for file in workflows_dir.glob("*.yml"):
        await sync_workflow(str(file))

if __name__ == "__main__":
    asyncio.run(main())
