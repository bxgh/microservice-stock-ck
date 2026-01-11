import subprocess
import re
import time
import os
import yaml

CONFIG_DIR = "/home/bxgh/microservice-stock/services/gsd-worker/config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "hs300_stocks.yaml")
BACKUP_FILE = os.path.join(CONFIG_DIR, "hs300_stocks.yaml.bak")

# 20 stocks for benchmarking (Select valid codes that likely have data)
TEST_STOCKS = [
    "000001", "000002", "600000", "600036", "600519", "000858", "601318", "600276", "600030", "002415",
    "000333", "601888", "300750", "300059", "603288", "002475", "601012", "601166", "600887", "002352"
]

def setup_config():
    if os.path.exists(CONFIG_FILE):
        os.rename(CONFIG_FILE, BACKUP_FILE)
    
    with open(CONFIG_FILE, "w") as f:
        yaml.dump({"stocks": TEST_STOCKS}, f)
    print(f"Created config with {len(TEST_STOCKS)} stocks.", flush=True)

def restore_config():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
    if os.path.exists(BACKUP_FILE):
        os.rename(BACKUP_FILE, CONFIG_FILE)
    print("Restored original config.", flush=True)

def run_test(concurrency):
    print(f"\n--- Testing Concurrency: {concurrency} ---", flush=True)
    cmd = [
        "docker", "run", "--rm", "--network", "host",
        "--env-file", ".env",
        "-e", "MOOTDX_API_URL=http://127.0.0.1:8003", 
        "-e", "CLICKHOUSE_HOST=127.0.0.1", 
        "-e", "no_proxy=127.0.0.1,localhost", # Bypass proxy for local services
        "-v", f"{os.getcwd()}/data/gsd-worker:/app/data",
        "-v", f"{os.getcwd()}/libs/gsd-shared:/app/libs/gsd-shared:ro",
        "-v", f"{os.getcwd()}/services/gsd-worker/config:/app/config:ro", 
        "-v", f"{os.getcwd()}/services/gsd-worker/src:/app/src", # Mount updated code
        "gsd-worker", "jobs.sync_tick",
        "--scope", "config",
        "--concurrency", str(concurrency)
    ]
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, cwd="/home/bxgh/microservice-stock")
    total_time = time.time() - start_time
    
    # Try to parse exact internal time from logs
    match = re.search(r"耗时 ([\d\.]+)s", result.stderr)
    if match:
        internal_time = float(match.group(1))
    else:
        internal_time = total_time # Fallback
        
    print(f"Concurrency {concurrency}: Internal={internal_time:.2f}s, Total={total_time:.2f}s", flush=True)
    if result.returncode != 0:
        print("Error output:", result.stderr[-500:], flush=True)
        
    return internal_time

def main():
    try:
        setup_config()
        results = {}
        for c in [1, 3, 6, 8, 12, 20]:
            duration = run_test(c)
            results[c] = duration
            # Cool down
            time.sleep(1)
            
        print("\n=== Benchmark Results ===", flush=True)
        print(f"{'Concurrency':<12} | {'Time (s)':<10} | {'Speedup':<10}", flush=True)
        print("-" * 38, flush=True)
        base_time = results[1]
        for c, t in results.items():
            speedup = base_time / t if t > 0 else 0
            print(f"{c:<12} | {t:<10.2f} | {speedup:<10.2f}x", flush=True)
            
    finally:
        restore_config()

if __name__ == "__main__":
    main()
