
import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8081/api/v1/tasks"

def update_task():
    # 1. List tasks
    try:
        resp = requests.get(BASE_URL)
        resp.raise_for_status()
        tasks = resp.json()
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        return

    logger.info(f"Tasks response type: {type(tasks)}")
    logger.info(f"Tasks response content: {json.dumps(tasks, indent=2, ensure_ascii=False)}")
    
    # Handle if tasks is wrapped in a dict
    if isinstance(tasks, dict) and 'data' in tasks:
        tasks = tasks['data']
    
    if isinstance(tasks, dict) and 'tasks' in tasks:
        tasks = tasks['tasks']

    # 2. Find target task
    target_task = None
    target_task_id = None
    
    for t in tasks:
        # Check 'name' directly or inside 'definition'
        name = t.get('name') or t.get('definition', {}).get('name')
        if name == "Daily K-Line Sync":
            target_task = t.get('definition', t) # Use definition for updates if possible, or just the dict
            target_task_id = t.get('id') or t.get('task_id')
            break
    
    if not target_task or not target_task_id:
        logger.warning("Task 'Daily K-Line Sync' not found. Creating new...")
        create_new_task()
        return

    logger.info(f"Found existing task: {target_task_id}, Cron: {target_task.get('cron_expression')}")
    
    task_id = target_task_id
    update_payload = target_task.copy()
    update_payload['cron_expression'] = "0 19 * * *"
    
    # Ensure config 'data' is properly JSON stringified double encoded if needed?
    # In the view_file, it was json.dumps in the script.
    # The GET response likely returns it as it is stored.
    # We should be careful. Let's just update the cron.
    
    update_url = f"{BASE_URL}/{task_id}"
    try:
        put_resp = requests.put(update_url, json=update_payload)
        if put_resp.status_code in [200, 204]:
            logger.info(f"✅ Task updated successfully to 19:00 (ID: {task_id})")
        else:
            logger.warning(f"PUT failed ({put_resp.status_code}), trying DELETE + CREATE. Resp: {put_resp.text}")
            # Fallback to delete and recreate
            requests.delete(update_url)
            create_new_task()
            
    except Exception as e:
        logger.error(f"Update failed: {e}")

def create_new_task():
    payload = {
      "name": "Daily K-Line Sync",
      "task_type": "http",
      "description": "Daily incremental K-line synchronization from MySQL to ClickHouse. Uses 'smart' mode to fetch only new data.",
      "cron_expression": "0 19 * * *",
      "config": {
        "url": "http://172.17.0.1:8083/api/v1/sync/kline",
        "method": "POST",
        "data": json.dumps({"mode": "smart"})
      }
    }
    resp = requests.post(BASE_URL, json=payload)
    if resp.status_code in [200, 201]:
        logger.info(f"✅ New task created successfully (ID: {resp.json().get('id')})")
    else:
        logger.error(f"Failed to create task: {resp.text}")

if __name__ == "__main__":
    update_task()
