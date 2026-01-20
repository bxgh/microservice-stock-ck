#!/bin/bash
# ops/deploy_node_58.sh
# Server 58 (Worker Shard 1) 智能部署脚本
# 用法: ./deploy_node_58.sh [branch_name] [services]
# 参数:
#   $1 - 分支名，默认 main
#   $2 - 要部署的服务列表 (逗号分隔)，如 "mootdx-api,gsd-worker"
#        如果为空，则跳过服务部署

BRANCH_NAME="${1:-main}"
SERVICES="${2:-}"
LOG_FILE="/home/bxgh/microservice-stock/logs/deploy_58.log"
mkdir -p $(dirname $LOG_FILE)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "=== 开始部署 Server 58 (Remote Worker Mode) ==="
log "目标分支: $BRANCH_NAME"
log "目标服务: ${SERVICES:-无 (仅同步代码)}"

# 1. 切换到项目根目录
cd /home/bxgh/microservice-stock

# 2. 同步代码
log "正在拉取最新代码 ($BRANCH_NAME)..."
git fetch --all
git checkout $BRANCH_NAME
git reset --hard origin/$BRANCH_NAME

# 3. 如果没有指定服务，只同步代码不部署
if [ -z "$SERVICES" ]; then
    log "无需部署服务，仅完成代码同步"
    log "=== Server 58 代码同步完成 ==="
    exit 0
fi

# 4. 解析服务列表并部署
log "正在部署服务..."

# 将逗号分隔的字符串转为数组
IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"

# 用于 docker-compose.node-58.yml 的服务
COMPOSE_SERVICES=()

# 是否需要部署 shard-poller
DEPLOY_POLLER=false

for service in "${SERVICE_ARRAY[@]}"; do
    case "$service" in
        "mootdx-api"|"mootdx-source"|"gsd-worker")
            COMPOSE_SERVICES+=("$service")
            log "  -> 将部署: $service"
            ;;
        "shard-poller")
            DEPLOY_POLLER=true
            log "  -> 将部署: shard-poller"
            ;;
        *)
            log "  -> 跳过不支持的服务: $service"
            ;;
    esac
done

# 5. 部署业务服务 (如果有)
if [ ${#COMPOSE_SERVICES[@]} -gt 0 ]; then
    log "正在部署业务服务: ${COMPOSE_SERVICES[*]}"
    docker compose -f docker-compose.node-58.yml up -d --build "${COMPOSE_SERVICES[@]}"
fi

# 6. 部署 shard-poller (如果需要)
# 检查是否在 SERVICES 中请求了 shard-poller
if [[ ",$SERVICES," == *",shard-poller,"* ]]; then
    log "正在部署 shard-poller..."
    docker compose -f services/task-orchestrator/docker-compose.poller-58.yml up -d --build shard-poller
fi

log "=== Server 58 部署完成 ==="
