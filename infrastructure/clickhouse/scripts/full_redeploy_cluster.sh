#!/bin/bash

# full_redeploy.sh
# 完全清除并重新部署 ClickHouse 集群
# 包含：清理数据、分发配置、顺序启动

set -e

# 配置
SSH_OPTS="-o StrictHostKeyChecking=no -o BatchMode=yes"
REMOTE_DIR="/home/bxgh/microservice-stock-deploy/clickhouse"
CURRENT_DIR=$(pwd)

echo "===== Step 1: 停止所有节点 ====="
docker stop microservice-stock-clickhouse || true
docker rm -f microservice-stock-clickhouse || true

ssh $SSH_OPTS bxgh@192.168.151.58 "docker stop microservice-stock-clickhouse && docker rm -f microservice-stock-clickhouse" || true
ssh $SSH_OPTS bxgh@192.168.151.111 "docker stop microservice-stock-clickhouse && docker rm -f microservice-stock-clickhouse" || true
echo "所有节点容器已停止并删除"
echo

echo "===== Step 2: 清理数据 (DANGER) ====="
# 仅清理 Keeper 数据以重置集群状态，保留表数据可选（这里全清以确保干净）
docker volume rm microservice-stock_clickhouse_data microservice-stock_clickhouse_logs || true
docker volume create microservice-stock_clickhouse_data
docker volume create microservice-stock_clickhouse_logs

ssh $SSH_OPTS bxgh@192.168.151.58 "docker volume rm microservice-stock_clickhouse_data microservice-stock_clickhouse_logs && docker volume create microservice-stock_clickhouse_data && docker volume create microservice-stock_clickhouse_logs" || true
ssh $SSH_OPTS bxgh@192.168.151.111 "docker volume rm microservice-stock_clickhouse_data microservice-stock_clickhouse_logs && docker volume create microservice-stock_clickhouse_data && docker volume create microservice-stock_clickhouse_logs" || true
echo "所有节点数据卷已重建"
echo

echo "===== Step 3: 分发配置 ====="
# 创建远程目录
ssh $SSH_OPTS bxgh@192.168.151.58 "mkdir -p $REMOTE_DIR/config/config.d"
ssh $SSH_OPTS bxgh@192.168.151.111 "mkdir -p $REMOTE_DIR/config/config.d"

# 分发主配置文件
scp $SSH_OPTS deploy/clickhouse/config/config.xml bxgh@192.168.151.58:$REMOTE_DIR/config/
scp $SSH_OPTS deploy/clickhouse/config/config.xml bxgh@192.168.151.111:$REMOTE_DIR/config/
scp $SSH_OPTS deploy/clickhouse/config/users.xml bxgh@192.168.151.58:$REMOTE_DIR/config/
scp $SSH_OPTS deploy/clickhouse/config/users.xml bxgh@192.168.151.111:$REMOTE_DIR/config/

# 分发特定节点配置
scp $SSH_OPTS deploy/clickhouse/config/config.d/node_58.xml bxgh@192.168.151.58:$REMOTE_DIR/config/config.d/node_58.xml
scp $SSH_OPTS deploy/clickhouse/config/config.d/node_111.xml bxgh@192.168.151.111:$REMOTE_DIR/config/config.d/node_111.xml

echo "配置分发完成"
echo

echo "===== Step 4: 启动集群 ====="

# 启动 Node 1 (41) - 本地
echo "Starting Node 41..."
docker run -d --name microservice-stock-clickhouse \
  --restart unless-stopped \
  --network host \
  --ulimit nofile=262144:262144 \
  -v microservice-stock_clickhouse_data:/var/lib/clickhouse \
  -v microservice-stock_clickhouse_logs:/var/log/clickhouse-server \
  -v "$CURRENT_DIR/deploy/clickhouse/config/config.xml:/etc/clickhouse-server/config.xml" \
  -v "$CURRENT_DIR/deploy/clickhouse/config/users.xml:/etc/clickhouse-server/users.xml" \
  -v "$CURRENT_DIR/deploy/clickhouse/config/config.d/node_41.xml:/etc/clickhouse-server/config.d/node_41.xml" \
  clickhouse/clickhouse-server:latest

echo "Node 41 (Leader) 已启动"

# 启动 Node 2 (58) - 远程
echo "Starting Node 58..."
ssh $SSH_OPTS bxgh@192.168.151.58 "docker run -d --name microservice-stock-clickhouse \
  --restart unless-stopped \
  --network host \
  --ulimit nofile=262144:262144 \
  -v microservice-stock_clickhouse_data:/var/lib/clickhouse \
  -v microservice-stock_clickhouse_logs:/var/log/clickhouse-server \
  -v $REMOTE_DIR/config/config.xml:/etc/clickhouse-server/config.xml \
  -v $REMOTE_DIR/config/users.xml:/etc/clickhouse-server/users.xml \
  -v $REMOTE_DIR/config/config.d/node_58.xml:/etc/clickhouse-server/config.d/node_58.xml \
  clickhouse/clickhouse-server:latest"

echo "Node 58 已启动"

# 启动 Node 3 (111) - 远程
echo "Starting Node 111..."
ssh $SSH_OPTS bxgh@192.168.151.111 "docker run -d --name microservice-stock-clickhouse \
  --restart unless-stopped \
  --network host \
  --ulimit nofile=262144:262144 \
  -v microservice-stock_clickhouse_data:/var/lib/clickhouse \
  -v microservice-stock_clickhouse_logs:/var/log/clickhouse-server \
  -v $REMOTE_DIR/config/config.xml:/etc/clickhouse-server/config.xml \
  -v $REMOTE_DIR/config/users.xml:/etc/clickhouse-server/users.xml \
  -v $REMOTE_DIR/config/config.d/node_111.xml:/etc/clickhouse-server/config.d/node_111.xml \
  clickhouse/clickhouse-server:latest"

echo "Node 111 已启动"
echo "等待集群初始化 (30s)..."
sleep 30

echo "===== Step 5: 验证状态 ====="
echo "Checking Keeper status on Node 41..."
echo mntr | nc -w 5 127.0.0.1 9181
