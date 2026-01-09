#!/bin/bash

# deploy_cluster_compose.sh
# 使用 Docker Compose 部署 ClickHouse 集群（替代 full_redeploy_cluster.sh）

set -e

SSH_OPTS="-o StrictHostKeyChecking=no -o BatchMode=yes"
CURRENT_DIR=$(pwd)

echo "===== ClickHouse Cluster Docker Compose Deployment ====="
echo

# 确保在正确的目录
if [[ ! -d "infrastructure/clickhouse" ]]; then
    echo "错误: 请在项目根目录运行此脚本"
    exit 1
fi

echo "[1/4] 分发配置文件到远程节点..."
scp $SSH_OPTS -r infrastructure/clickhouse/config/ bxgh@192.168.151.58:~/microservice-stock-deploy/clickhouse/
scp $SSH_OPTS -r infrastructure/clickhouse/config/ bxgh@192.168.151.111:~/microservice-stock-deploy/clickhouse/

# 分发 Docker Compose 文件
scp $SSH_OPTS infrastructure/clickhouse/docker-compose.node-58.yml bxgh@192.168.151.58:~/microservice-stock-deploy/clickhouse/
scp $SSH_OPTS infrastructure/clickhouse/docker-compose.node-111.yml bxgh@192.168.151.111:~/microservice-stock-deploy/clickhouse/

echo "配置分发完成"
echo

echo "[2/4] 启动 Server 41 (Leader)..."
cd infrastructure/clickhouse
docker-compose -f docker-compose.node-41.yml up -d
cd "$CURRENT_DIR"
echo "Server 41 已启动"
sleep 5

echo "[3/4] 启动 Server 58..."
ssh $SSH_OPTS bxgh@192.168.151.58 "cd ~/microservice-stock-deploy/clickhouse && docker-compose -f docker-compose.node-58.yml up -d"
echo "Server 58 已启动"
sleep 5

echo "[4/4] 启动 Server 111..."
ssh $SSH_OPTS bxgh@192.168.151.111 "cd ~/microservice-stock-deploy/clickhouse && docker-compose -f docker-compose.node-111.yml up -d"
echo "Server 111 已启动"
sleep 10

echo
echo "===== 验证集群状态 ====="
echo "Keeper 状态 (Server 41):"
echo mntr | nc -w 3 127.0.0.1 9181

echo
echo "===== 部署完成 ====="
echo
echo "后续操作:"
echo "1. 查看日志: docker-compose -f infrastructure/clickhouse/docker-compose.node-41.yml logs -f"
echo "2. 查看集群: docker exec microservice-stock-clickhouse clickhouse-client --query \"SELECT * FROM system.clusters WHERE cluster='stock_cluster'\""
echo "3. 停止集群: ./infrastructure/clickhouse/scripts/stop_cluster_compose.sh"
