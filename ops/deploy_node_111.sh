#!/bin/bash
# ops/deploy_node_111.sh
# Server 111 (Worker Shard 2) 专用部署脚本
# 特点：强制拉取 feature/redis-stream-refactor 分支

BRANCH_NAME="feature/redis-stream-refactor"
LOG_FILE="/home/bxgh/microservice-stock/logs/deploy_111.log"
mkdir -p $(dirname $LOG_FILE)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "=== 开始部署 Server 111 (Remote Worker Mode) ==="

# 1. 切换到项目根目录
cd /home/bxgh/microservice-stock

# 2. 同步代码
log "正在拉取最新代码 ($BRANCH_NAME)..."
git fetch --all
git checkout $BRANCH_NAME
git reset --hard origin/$BRANCH_NAME

# 3. 部署服务
log "正在部署服务 (Docker Compose)..."
# 使用 docker-compose.node-111.yml 构建并启动
# Explicitly deploy business services
docker compose -f docker-compose.node-111.yml up -d --build gsd-worker mootdx-api mootdx-source

log "=== Server 111 部署完成 ==="
