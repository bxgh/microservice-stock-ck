#!/bin/bash

# Default to 2026-01-08 if no date provided
TARGET_DATE=${1:-20260108}

echo "=================================================="
echo "   TDX Verification (Native System Tunnel :8118)"
echo "   Target Date: $TARGET_DATE"
echo "=================================================="

# 1. Check Native Tunnel Port
echo "[1/3] Checking System SOCKS5 Tunnel (Port 8118)..."
if ! lsof -i:8118 -t >/dev/null; then
    echo "❌ System tunnel on port 8118 NOT found!"
    echo "   Please ask the administrator to start the system ssh tunnel."
    exit 1
else
    echo "✅  System tunnel is active on port 8118."
fi

# 2. Restart API (already configured for 8118 in docker-compose)
echo "[2/3] Ensuring mootdx-api is ready..."
docker restart microservice-stock-mootdx-api
sleep 5

# 3. Publish & Monitor
echo "[3/3] Starting Benchmark..."
docker compose -f docker-compose.node-41.yml run --rm \
    gsd-worker jobs.run_stream_tick publisher --date $TARGET_DATE

echo ""
echo "--- Monitoring Processing Progress (Ctrl+C to stop) ---"

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
