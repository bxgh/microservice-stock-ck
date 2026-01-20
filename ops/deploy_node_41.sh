#!/bin/bash
# ops/deploy_node_41.sh
# Server 41 (Master/Dev) 专用部署脚本
# 特点：使用本地代码构建（不拉取 Git），保留开发进度

# 设置日志文件
LOG_FILE="/home/bxgh/microservice-stock/logs/deploy_41.log"
mkdir -p $(dirname $LOG_FILE)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "=== 开始部署 Server 41 (Local Dev Mode) ==="

# 1. 切换到项目根目录
cd /home/bxgh/microservice-stock

# 2. 部署核心服务
log "正在部署服务 (Docker Compose)..."
# 使用 docker-compose.node-41.yml 构建并启动
# 包含: task-orchestrator, get-stockdata, mootdx-api, redis, etc.
docker compose -f docker-compose.node-41.yml up -d --build

log "=== Server 41 部署完成 ==="
