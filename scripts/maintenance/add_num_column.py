import subprocess
import sys
import time

# Configuration
# Assuming we are running this from the same context as migrate_clickhouse_full.py
# which seems to run on the host or a container with access to docker.
# 
# We will try to execute against the local container first.
CLICKHOUSE_CONTAINER = "microservice-stock-clickhouse"
DB_NAME = "stock_data"

def run_query(query):
    """Run a query using docker exec clickhouse-client"""
    cmd = [
        "docker", "exec", CLICKHOUSE_CONTAINER, 
        "clickhouse-client", "--database", DB_NAME, "--query", query
    ]
    
    print(f"Executing: {query}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return result.stdout.strip()

def check_column_exists(table, column):
    query = f"SELECT count() FROM system.columns WHERE database='{DB_NAME}' AND table='{table}' AND name='{column}'"
    res = run_query(query)
    return res and int(res) > 0

def add_column(table):
    if not check_column_exists(table, "num"):
        # Check if table exists first
        check_table = f"EXISTS table {table}"
        if run_query(check_table) == "1":
            print(f"Adding 'num' column to {table}...")
            # Using ON CLUSTER if it's a distributed/replicated setup, but for safety let's try local first
            # If it's Replicated, getting it on one replica might be enough if automatic DDL replication is on, 
            # but usually usually ALTER need to be run on all replicas or use ON CLUSTER.
            # However, I will try basic ALTER first.
            
            # Note: For ReplicatedMergeTree, ALTER is replicated to all replicas if run on one (usually).
            sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS num UInt32 DEFAULT 0 COMMENT '成交笔数' AFTER direction"
            run_query(sql)
            print(f"Done adding to {table}.")
        else:
            print(f"Table {table} does not exist.")
    else:
        print(f"Column 'num' already exists in {table}.")

def main():
    print("Starting schema migration...")
    
    # Tables to update
    tables = ["tick_data", "tick_data_intraday_local"]
    
    for t in tables:
        add_column(t)
        
    print("Migration finished.")

if __name__ == "__main__":
    main()
