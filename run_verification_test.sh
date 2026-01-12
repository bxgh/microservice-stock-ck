#!/bin/bash

# Default to 2026-01-08 if no date provided
TARGET_DATE=${1:-20260108}

echo "=================================================="
echo "   TDX Data Acquisition Verification Script"
echo "   Target Date: $TARGET_DATE"
echo "=================================================="

# 1. Ensure SSH Tunnel is Active
echo "[1/4] Checking SOCKS5 Tunnel (Port 1080)..."
if ! lsof -i:1080 -t >/dev/null; then
    echo "⚠️  Tunnel not found. Starting setup_ssh_tunnel.sh..."
    ./setup_ssh_tunnel.sh
    sleep 3
else
    echo "✅  Tunnel is active."
fi

# 2. Restart API to ensure Clean State & SOCKS Env
echo "[2/4] Ensuring mootdx-api is ready..."
docker restart microservice-stock-mootdx-api
echo "Waiting 5s for initialization..."
sleep 5

# 3. Publish Jobs
echo "[3/4] Publishing Full Market Jobs..."
docker compose -f docker-compose.node-41.yml run --rm \
    gsd-worker jobs.run_stream_tick publisher --date $TARGET_DATE

# 4. Monitor Progress
echo "[4/4] Monitoring Processing Progress..."
echo "      (Press Ctrl+C to stop monitoring when 'Jobs Pending' reaches 0)"
echo ""

while true; do
    STATS=$(docker exec microservice-stock-mootdx-api python3 -c "
from redis.cluster import RedisCluster
try:
    r = RedisCluster(host='127.0.0.1', port=16379, decode_responses=True)
    pending = r.xpending('stream:tick:jobs', 'group:mootdx:workers')['pending']
    results = r.xlen('stream:tick:data')
    print(f'{pending}|{results}')
except Exception:
    print('Error|Error')
")
    
    PENDING=$(echo $STATS | cut -d'|' -f1)
    RESULTS=$(echo $STATS | cut -d'|' -f2)
    
    # Get ClickHouse Count
    CK_COUNT=$(docker exec microservice-stock-clickhouse clickhouse-client --query "SELECT count(*) FROM stock_data.tick_data WHERE trade_date='${TARGET_DATE:0:4}-${TARGET_DATE:4:2}-${TARGET_DATE:6:2}'")
    
    echo "$(date '+%H:%M:%S') - Pending Jobs: $PENDING  |  Redis Stream Results: $RESULTS  |  ClickHouse Rows: $CK_COUNT"
    
    sleep 3
done
