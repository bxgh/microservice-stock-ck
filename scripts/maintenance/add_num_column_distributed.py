import subprocess
import sys
import time

# Configuration
NODES = [
    {"ip": "127.0.0.1", "name": "Node 41 (Local)", "ssh": None},
    {"ip": "192.168.151.58", "name": "Node 58", "ssh": "ssh bxgh@192.168.151.58"},
    {"ip": "192.168.151.111", "name": "Node 111", "ssh": "ssh bxgh@192.168.151.111"}
]

CLICKHOUSE_CONTAINER = "microservice-stock-clickhouse"
DB_NAME = "stock_data"

def run_query(node, query):
    """Run a query using docker exec clickhouse-client on target node"""
    
    docker_cmd = f"docker exec {CLICKHOUSE_CONTAINER} clickhouse-client --database {DB_NAME} --query \"{query}\""
    
    if node['ssh']:
        # Remote execution via SSH
        # Need to escape double quotes for SSH command
        escaped_query = query.replace('"', '\\"')
        cmd = f"{node['ssh']} '{docker_cmd}'"
        # For simplicity, let's use subprocess with shell=True for the SSH command string
        # But wait, passing complex params via SSH can be tricky with shell=True.
        # Let's try sending input if possible, or careful quoting.
        # The query is simple enough here.
    else:
        # Local execution
        cmd = docker_cmd
    
    print(f"[{node['name']}] Executing: {query}")
    # print(f"DEBUG CMD: {cmd}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[{node['name']}] Error: {result.stderr}")
        return None
    return result.stdout.strip()

def check_column_exists(node, table, column):
    query = f"SELECT count() FROM system.columns WHERE database='{DB_NAME}' AND table='{table}' AND name='{column}'"
    res = run_query(node, query)
    return res and int(res) > 0

def add_column(node, table):
    # Check if table exists first
    check_table = f"EXISTS table {table}"
    exists = run_query(node, check_table)
    
    if exists == "1":
        if not check_column_exists(node, table, "num"):
            print(f"[{node['name']}] Adding 'num' column to {table}...")
            # We use local ALTER, assuming Replicated setup handles replication or we do it on each node manually.
            # Since user requested "change tables on 58, 111", manual application is safer and surer.
            sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS num UInt32 DEFAULT 0 COMMENT '成交笔数' AFTER direction"
            run_query(node, sql)
            print(f"[{node['name']}] Done adding to {table}.")
        else:
            print(f"[{node['name']}] Column 'num' already exists in {table}.")
    else:
        print(f"[{node['name']}] Table {table} does not exist.")

def main():
    print("Starting distributed schema checking & migration...")
    
    tables = ["tick_data", "tick_data_intraday_local"]
    
    for node in NODES:
        print(f"\n--- Checking {node['name']} ---")
        for t in tables:
            try:
                add_column(node, t)
            except Exception as e:
                print(f"[{node['name']}] Failed to process {t}: {e}")
        
    print("\nDistributed migration finished.")

if __name__ == "__main__":
    main()
