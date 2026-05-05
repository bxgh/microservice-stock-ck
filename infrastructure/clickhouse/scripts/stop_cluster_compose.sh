#!/bin/bash

# stop_cluster_compose.sh
# 停止 ClickHouse 集群 (Docker Compose 方式)

set -e

SSH_OPTS="-o StrictHostKeyChecking=no -o BatchMode=yes"
CURRENT_DIR=$(pwd)

echo "===== Stopping ClickHouse Cluster ====="
echo

echo "[1/3] 停止 Server 111..."
ssh $SSH_OPTS bxgh@192.168.151.111 "cd ~/microservice-stock-deploy/clickhouse && docker-compose -f docker-compose.node-111.yml down" || true

echo "[2/3] 停止 Server 58..."
ssh $SSH_OPTS bxgh@192.168.151.58 "cd ~/microservice-stock-deploy/clickhouse && docker-compose -f docker-compose.node-58.yml down" || true

echo "[3/3] 停止 Server 41..."
cd infrastructure/clickhouse
docker-compose -f docker-compose.node-41.yml down || true
cd "$CURRENT_DIR"

echo
echo "集群已全部停止"
