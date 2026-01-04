import subprocess
import json
import re
import time
import sys

# Configuration
EXCLUDED_TABLES = [
    'time_series_observations', 
    'snapshot_daily_stats',     
    'stock_kline_daily',        
    'stock_kline_daily_backup', 
    'test_replication',
    # skip system/inner tables automatically
]

def run_query(server_id, query, dry_run=False):
    if dry_run:
        print(f"[DRY-RUN] {server_id}: {query}")
        return ""
    
    # Clean up query: remove excessive escaping if present from previous failures
    query = query.replace('\\n', '\n') 
    
    if server_id == 41:
        # Use docker exec with stdin
        cmd = ["docker", "exec", "-i", "microservice-stock-clickhouse", "clickhouse-client"]
        # run with process input
        result = subprocess.run(cmd, input=query, text=True, capture_output=True)
    else:
        # Server 58: SSH + docker exec -i
        # We constructed the ssh command to pipe input into docker
        ssh_cmd = "ssh bxgh@192.168.151.58 'docker exec -i microservice-stock-clickhouse clickhouse-client'"
        result = subprocess.run(ssh_cmd, input=query, shell=True, text=True, capture_output=True)

    if result.returncode != 0:
        print(f"ERROR executing on {server_id}: {query[:200]}...") # truncate log
        print(f"Stderr: {result.stderr}")
        raise Exception(f"Query failed on {server_id}")
    
    return result.stdout.strip()

def get_tables():
    output = run_query(41, "SELECT name, engine FROM system.tables WHERE database='stock_data'")
    tables = []
    for line in output.split('\n'):
        if not line: continue
        parts = line.split('\t')
        if len(parts) < 2: continue
        name, engine = parts[0], parts[1]
        
        if name in EXCLUDED_TABLES: continue
        if 'Backup' in name or 'backup' in name: continue
        if name.startswith('.inner'): continue
        if 'Replicated' in engine: continue 
        if 'View' in engine: continue       
        tables.append((name, engine))
    return tables

def transform_schema(table_name, create_sql):
    # Fix DB prefix
    create_sql = create_sql.replace(f"CREATE TABLE {table_name}", f"CREATE TABLE stock_data.{table_name}")
    
    # Clean up any potential \n mess if python returned raw string
    create_sql = create_sql.replace('\\n', '\n').replace("\\'", "'")

    # Regex search for ENGINE
    # ReplacingMergeTree
    match = re.search(r"ENGINE = ReplacingMergeTree(\(.*\))?", create_sql)
    if match:
        full_engine_str = match.group(0)
        params_with_parens = match.group(1) if match.group(1) else ""
        
        if params_with_parens:
            # (update_time) -> update_time
            inner = params_with_parens.strip("()")
            new_engine = f"ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{{shard}}/{table_name}', '{{replica}}', {inner})"
        else:
            new_engine = f"ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{{shard}}/{table_name}', '{{replica}}')"
        
        return create_sql.replace(full_engine_str, new_engine)
        
    # MergeTree
    match = re.search(r"ENGINE = MergeTree", create_sql)
    if match:
        new_engine = f"ENGINE = ReplicatedMergeTree('/clickhouse/tables/{{shard}}/{table_name}', '{{replica}}')"
        return create_sql.replace("ENGINE = MergeTree", new_engine)

    # SummingMergeTree
    match = re.search(r"ENGINE = SummingMergeTree(\(.*\))?", create_sql)
    if match:
        full_engine_str = match.group(0)
        params_with_parens = match.group(1) if match.group(1) else ""
        if params_with_parens:
            inner = params_with_parens.strip("()")
            new_engine = f"ENGINE = ReplicatedSummingMergeTree('/clickhouse/tables/{{shard}}/{table_name}', '{{replica}}', {inner})"
        else:
             new_engine = f"ENGINE = ReplicatedSummingMergeTree('/clickhouse/tables/{{shard}}/{table_name}', '{{replica}}')"
        return create_sql.replace(full_engine_str, new_engine)

    raise Exception(f"Unsupported engine in: {create_sql[:100]}...")

def migrate_table(name, engine):
    print(f"\n>>> Migrating {name} ({engine})...")
    
    # 1. Get Schema
    create_sql = run_query(41, f"SHOW CREATE TABLE stock_data.{name}")
    new_create_sql = transform_schema(name, create_sql)
    
    # 2. Rename
    print(f"  Renaming {name} to {name}_backup...")
    # Consider idempotency: check if backup exists or table exists?
    # Simple retry: ignore error if backup rename fails? No, risky.
    # We assume clean state.
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
    # Wait a bit for sync? Usually fast for local metadata.
    time.sleep(1)
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
    try:
        tables = get_tables()
        print(f"Found {len(tables)} tables to migrate: {[t[0] for t in tables]}")
        
        for name, engine in tables:
            try:
                migrate_table(name, engine)
            except Exception as e:
                print(f"FAILED to migrate {name}: {e}")
                # Don't exit, try next table? Or stop?
                # Better stop to prevent cascading failures
                sys.exit(1)
    except Exception as e:
        print(f"Global Error: {e}")
        sys.exit(1)
            
    print("\nAll migrations completed.")

if __name__ == "__main__":
    main()
