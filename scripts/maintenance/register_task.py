
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

url = "http://localhost:8081/api/v1/tasks"
payload = {
  "name": "Daily K-Line Sync",
  "task_type": "http",
  "description": "Daily incremental K-line synchronization from MySQL to ClickHouse. Uses 'smart' mode to fetch only new data.",
  "cron_expression": "0 2 * * *",
  "config": {
    "url": "http://172.17.0.1:8083/api/v1/sync/kline",
    "method": "POST",
    "data": json.dumps({
       "mode": "smart"
    })
  }
}

try:
    response = requests.post(url, json=payload)
    if response.status_code in [200, 201]:
        logger.info("Task created successfully:")
        logger.info(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        logger.error(f"Failed to create task. Status: {response.status_code}")
        logger.error(response.text)
except Exception as e:
    logger.error(f"Error: {e}")
