import pymysql
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cloud MySQL Config (via Tunnel)
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 36301,
    'user': 'root',
    'password': 'alwaysup@888',
    'database': 'alwaysup',
    'autocommit': True
}

def wait_for_status(conn, cmd_id, target_status=['DONE', 'FAILED'], timeout=60):
    start = time.time()
    with conn.cursor() as cursor:
        while time.time() - start < timeout:
            cursor.execute("SELECT status, result FROM task_commands WHERE id=%s", (cmd_id,))
            row = cursor.fetchone()
            if row:
                status, result = row
                logger.info(f"Command #{cmd_id} status: {status}")
                if status in target_status:
                    return status, result
            time.sleep(2)
    return "TIMEOUT", None

def main():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        logger.info("Connected to Cloud MySQL via Tunnel")
        
        with conn.cursor() as cursor:
            # 1. Clean up old test commands
            cursor.execute("DELETE FROM task_commands WHERE task_id='repair_kline' AND status='PENDING'")
            
            # 2. Insert test command
            params = json.dumps({"date": "20260113"})
            sql = "INSERT INTO task_commands (task_id, params, status) VALUES (%s, %s, 'PENDING')"
            cursor.execute(sql, ('repair_kline', params))
            cmd_id = cursor.lastrowid
            logger.info(f"Inserted test command #{cmd_id} (repair_kline, date=20260113)")
            
        # 3. Wait for execution
        logger.info("Waiting for execution...")
        status, result = wait_for_status(conn, cmd_id, timeout=120)
        
        if status == "DONE":
            logger.info(f"✅ Test Passed! Result: {result}")
        elif status == "FAILED":
            logger.error(f"❌ Test Failed! Error: {result}")
        else:
            logger.error(f"❌ Test Timeout! Status: {status}")

    except Exception as e:
        logger.error(f"Test Exception: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
