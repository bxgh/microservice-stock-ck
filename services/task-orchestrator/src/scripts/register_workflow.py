import asyncio
import yaml
import json
import aiomysql
import sys
import os
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

async def register_workflow(file_path: str):
    """Register a workflow YAML definition into MySQL"""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        
    wf = data.get("workflow")
    if not wf:
        print("Error: Missing 'workflow' key in YAML")
        return

    wf_id = wf["id"]
    wf_name = wf["name"]
    
    # Store the entire workflow structure as JSON
    definition_json = json.dumps(wf)

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
    print(f"✅ Workflow '{wf_id}' registered successfully.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python register_workflow.py <path_to_yaml>")
        sys.exit(1)
    
    asyncio.run(register_workflow(sys.argv[1]))
