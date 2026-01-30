import subprocess
import sys

# Configuration
NODES = [
    {"ip": "127.0.0.1", "name": "Node 41 (Local)", "ssh": None},
    {"ip": "192.168.151.58", "name": "Node 58", "ssh": "ssh bxgh@192.168.151.58"},
    {"ip": "192.168.151.111", "name": "Node 111", "ssh": "ssh bxgh@192.168.151.111"}
]

CLICKHOUSE_CONTAINER = "microservice-stock-clickhouse"
DB_NAME = "stock_data"
# Using English comment to avoid encoding issues via SSH
SQL_ADD_COLUMN = "ALTER TABLE tick_data_intraday ADD COLUMN IF NOT EXISTS num UInt32 DEFAULT 0 COMMENT 'TradeNum' AFTER direction"

def run_query(node, query):
    docker_cmd = f"docker exec {CLICKHOUSE_CONTAINER} clickhouse-client --database {DB_NAME} --query \"{query}\""
    
    if node['ssh']:
        cmd = f"{node['ssh']} '{docker_cmd}'"
    else:
        cmd = docker_cmd
    
    print(f"[{node['name']}] Executing: {query}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[{node['name']}] Error: {result.stderr}")
        return None
    return result.stdout.strip()

def main():
    print("Updating Distributed table schema (tick_data_intraday)...")
    
    for node in NODES:
        # Check if table exists
        exists = run_query(node, "EXISTS TABLE tick_data_intraday")
        if exists == "1":
             run_query(node, SQL_ADD_COLUMN)
             print(f"[{node['name']}] Success.")
        else:
             print(f"[{node['name']}] Table tick_data_intraday does not exist.")
             
    print("\nDone.")

if __name__ == "__main__":
    main()
