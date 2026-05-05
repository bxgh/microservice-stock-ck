#!/bin/bash
# ops/sync_deploy.sh
# 用于 Webhook 触发或手动执行的自动部署脚本

# 设置日志文件
LOG_FILE="/home/bxgh/microservice-stock/logs/deploy.log"
mkdir -p $(dirname $LOG_FILE)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "=== Starting Deployment ==="

# 1. 切换到项目根目录
cd /home/bxgh/microservice-stock

# 2. 拉取最新代码
log "Pulling latest code..."
git fetch --all

# 优先使用 feature 分支，如果不存在则回退到 main
BRANCH="feature/redis-stream-refactor"
git reset --hard origin/$BRANCH || git reset --hard origin/main
git pull

# 3. 核心服务镜像重构
log "Rebuilding images..."

# gsd-worker
log "Building gsd-worker..."
docker build -t gsd-worker:latest -f services/gsd-worker/Dockerfile . >> $LOG_FILE 2>&1

# intraday-tick-collector (新增)
log "Building intraday-tick-collector..."
docker build -t get-stockdata:latest \
  -f services/get-stockdata/Dockerfile . \
  --build-arg ENABLE_PROXY=true \
  --build-arg PROXY_URL=http://192.168.151.18:3128 \
  >> $LOG_FILE 2>&1

# mootdx-source (修复 Context 问题)
log "Building mootdx-source..."
docker compose -f docker-compose.node-58.yml build mootdx-source >> $LOG_FILE 2>&1

# mootdx-api
log "Building mootdx-api..."
docker compose -f docker-compose.node-58.yml build mootdx-api >> $LOG_FILE 2>&1

# task-orchestrator (包含 poller)
log "Building task-orchestrator..."
docker build -t task-orchestrator:latest \
  -f services/task-orchestrator/Dockerfile . \
  --build-arg ENABLE_PROXY=true \
  --build-arg PROXY_URL=http://192.168.151.18:3128 \
  >> $LOG_FILE 2>&1

# 4. 重启服务
log "Restarting services..."

# 重启 Poller
if docker ps -a | grep -q gsd-shard-poller; then
    docker restart gsd-shard-poller
    log "Restarted gsd-shard-poller"
fi

# 重启 Compose 服务 (mootdx-api, source, gsd-worker, intraday-tick-collector)
# 注意：这里假设脚本运行在 58 节点
docker compose -f docker-compose.node-58.yml up -d mootdx-api mootdx-source gsd-worker intraday-tick-collector
log "Restarted core microservices"

log "=== Deployment Completed ==="
