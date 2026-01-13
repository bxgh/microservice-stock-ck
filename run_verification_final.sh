#!/bin/bash

# Default to 2026-01-08 if no date provided
TARGET_DATE=${1:-20260108}

echo "=================================================="
echo "   TDX Verification (Standardized Direct Access)"
echo "   Config: TDX_BIND_IP=192.168.151.41"
echo "   Target Date: $TARGET_DATE"
echo "=================================================="

# 1. Check Policy Routing
echo "[1/3] Checking Host Routing Rules..."
if ip rule list | grep -q "192.168.151.41"; then
    echo "✅ Policy Routing Rule Found: from 192.168.151.41 lookup 100"
else
    echo "❌ Missing Policy Routing Rule! Direct binding will fail."
    echo "   Re-applying rule..."
    sudo ip route add default via 192.168.151.254 dev ens32 table 100 || true
    sudo ip rule add from 192.168.151.41/32 lookup 100 || true
fi

# 2. Restart API (already configured)
echo "[2/3] Checking mootdx-api status..."
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
from redis import Redis
try:
    r = Redis(host='127.0.0.1', port=6379, password='redis123', decode_responses=True)
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
