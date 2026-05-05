#!/bin/bash
set -e

# Config
PORT=16379
REQUESTS=100000
CLIENTS=50
DATA_SIZE=100  # 100 bytes payload

echo "========================================================"
echo "🚀 Redis 3-Shard Cluster Benchmark"
echo "========================================================"
echo "Cluster Configuration:"
echo "  - Port: $PORT"
echo "  - Requests: $REQUESTS"
echo "  - Parallel Clients: $CLIENTS"
echo "  - Data Size: $DATA_SIZE bytes"
echo "========================================================"
echo ""

run_benchmark() {
    local node_ip=$1
    local name=$2
    
    echo "--------------------------------------------------------"
    echo "Testing Node: $name ($node_ip)"
    echo "--------------------------------------------------------"
    
    # Check connectivity first
    if ! docker exec microservice-stock-redis redis-cli -h $node_ip -p $PORT ping > /dev/null 2>&1; then
        echo "❌ Cannot connect to $node_ip:$PORT"
        return
    fi

    # Benchmark SET using redis-benchmark running inside the container
    # -h: host, -p: port, -c: clients, -n: requests, -d: data size, -t: tests (set,get), --cluster: cluster mode
    echo "Running SET/GET benchmark..."
    docker exec microservice-stock-redis redis-benchmark \
        -h $node_ip -p $PORT \
        -c $CLIENTS -n $REQUESTS -d $DATA_SIZE \
        -t set,get \
        --cluster \
        -q  # quiet mode
        
    echo ""
}

# Test the cluster entry point (Node 41)
run_benchmark "192.168.151.41" "Server 41 (Master 1)"

# Test other nodes to ensure they handle traffic efficiently
run_benchmark "192.168.151.58" "Server 58 (Master 2)"
run_benchmark "192.168.151.111" "Server 111 (Master 3)"

echo "========================================================"
echo "✅ Benchmark Complete"
echo "========================================================"
