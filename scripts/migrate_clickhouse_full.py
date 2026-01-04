import subprocess
import json
import re
import time
import sys

# Configuration
SERVER_41_CMD = "docker exec microservice-stock-clickhouse clickhouse-client"
SERVER_58_CMD = 'ssh bxgh@192.168.151.58 "docker exec microservice-stock-clickhouse clickhouse-client"'

# SSH wrapper for 58 to avoid shell escaping issues with complex SQL
# We will write SQL to a temp file on 58 and execute it
SERVER_58_SSH_PREFIX = 'ssh bxgh@192.168.151.58'

EXCLUDED_TABLES = [
    'time_series_observations', # System or unknown
    'snapshot_daily_stats',     # Materialized View
    'stock_kline_daily',        # Already migrated
    'stock_kline_daily_backup', # Backup
    'test_replication',         # Test table
]

def run_query(server_id, query, dry_run=False):
    if dry_run:
        print(f"[DRY-RUN] {server_id}: {query}")
        return ""
    
    if server_id == 41:
        command = f"{SERVER_41_CMD} --query \"{query}\""
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
    else:
        # Server 58: Use SSH with piped input to avoid shell escaping hell
        ssh_cmd = f"ssh bxgh@192.168.151.58 'docker exec -i microservice-stock-clickhouse clickhouse-client'"
        result = subprocess.run(ssh_cmd, input=query, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR executing on {server_id}: {query}")
        print(f"Stderr: {result.stderr}")
        raise Exception(f"Query failed on {server_id}")
    
    return result.stdout.strip()

def get_tables():
    output = run_query(41, "SELECT name, engine FROM system.tables WHERE database='stock_data'")
    tables = []
    for line in output.split('\n'):
        if not line: continue
        name, engine = line.split('\t')
        if name in EXCLUDED_TABLES: continue
        if 'Backup' in name or 'backup' in name: continue
        if name.startswith('.inner'): continue
        if 'Replicated' in engine: continue # Already migrated
        if 'View' in engine: continue       # Skip Views
        tables.append((name, engine))
    return tables

def transform_schema(table_name, create_sql):
    # Ensure database prefix is there for consistency
    if f"CREATE TABLE {table_name}" in create_sql:
        create_sql = create_sql.replace(f"CREATE TABLE {table_name}", f"CREATE TABLE stock_data.{table_name}")
    
    if "ENGINE = ReplacingMergeTree" in create_sql:
        # Capture parameters
        match = re.search(r"ENGINE = ReplacingMergeTree\((.*?)\)", create_sql)
        params = match.group(1) if match else ""
        new_engine = f"ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{{shard}}/{table_name}', '{{replica}}', {params})"
        new_sql = re.sub(r"ENGINE = ReplacingMergeTree\(.*?\)", new_engine, create_sql)
    elif "ENGINE = MergeTree" in create_sql:
        new_engine = f"ENGINE = ReplicatedMergeTree('/clickhouse/tables/{{shard}}/{table_name}', '{{replica}}')"
        new_sql = re.sub(r"ENGINE = MergeTree", new_engine, create_sql)
    elif "ENGINE = SummingMergeTree" in create_sql:
         match = re.search(r"ENGINE = SummingMergeTree\((.*?)\)", create_sql)
         params = match.group(1) if match else ""
         new_engine = f"ENGINE = ReplicatedSummingMergeTree('/clickhouse/tables/{{shard}}/{table_name}', '{{replica}}', {params})"
         new_sql = re.sub(r"ENGINE = SummingMergeTree\(.*?\)", new_engine, create_sql)
    else:
        raise Exception(f"Unsupported engine in SQL: {create_sql}")
    
    return new_sql

def migrate_table(name, engine):
    print(f"\n>>> Migrating {name} ({engine})...")
    
    # 1. Get Schema
    create_sql = run_query(41, f"SHOW CREATE TABLE stock_data.{name}")
    new_create_sql = transform_schema(name, create_sql)
    
    # 2. Rename
    print(f"  Renaming {name} to {name}_backup...")
    run_query(41, f"RENAME TABLE stock_data.{name} TO stock_data.{name}_backup")
    run_query(58, f"RENAME TABLE stock_data.{name} TO stock_data.{name}_backup")
    
    # 3. Create New Table
    print(f"  Creating new Replicated table...")
    run_query(41, new_create_sql)
    run_query(58, new_create_sql)
    
    # 4. Insert Data
    print(f"  Inserting data from backup (this may take time)...")
    start_time = time.time()
    run_query(41, f"INSERT INTO stock_data.{name} SELECT * FROM stock_data.{name}_backup")
    duration = time.time() - start_time
    print(f"  Data insertion completed in {duration:.1f}s")
    
    # 5. Verify
    verify_sync(name)

def verify_sync(name):
    print(f"  Verifying {name}...")
    c41 = int(run_query(41, f"SELECT count() FROM stock_data.{name}"))
    c58 = int(run_query(58, f"SELECT count() FROM stock_data.{name}"))
    
    print(f"    Server 41: {c41}")
    print(f"    Server 58: {c58}")
    
    if c41 == c58:
        print(f"    SUCCESS: Data synced.")
    else:
        print(f"    WARNING: Count mismatch! (Sync might be lagging)")

def main():
    tables = get_tables()
    print(f"Found {len(tables)} tables to migrate: {[t[0] for t in tables]}")
    
    for name, engine in tables:
        try:
            migrate_table(name, engine)
        except Exception as e:
            print(f"FAILED to migrate {name}: {e}")
            # Try to rollback rename on 41 if it failed early?
            # For now, just stop to let user inspect
            sys.exit(1)
            
    print("\nAll migrations completed.")

if __name__ == "__main__":
    main()
