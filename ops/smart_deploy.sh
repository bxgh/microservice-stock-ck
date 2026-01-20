#!/bin/bash
# ops/smart_deploy.sh
# 智能部署脚本 - 根据 Git 变更自动决定需要重建的服务

set -e

LOG_FILE="/home/bxgh/microservice-stock/logs/smart_deploy.log"
mkdir -p $(dirname $LOG_FILE)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

cd /home/bxgh/microservice-stock

# 获取本机 IP
CURRENT_IP=$(hostname -I | grep -o "192.168.151.[0-9]*" | head -n 1)
log "=== Smart Deploy Starting (IP: $CURRENT_IP) ==="

# 确定使用的 compose 文件
case "$CURRENT_IP" in
    "192.168.151.41")  COMPOSE_FILE="docker-compose.node-41.yml" ;;
    "192.168.151.58")  COMPOSE_FILE="docker-compose.node-58.yml" ;;
    "192.168.151.111") COMPOSE_FILE="docker-compose.node-111.yml" ;;
    *)
        log "Error: Unknown IP $CURRENT_IP"
        exit 1
        ;;
esac

# 获取上一次部署的 commit (存储在本地文件)
LAST_DEPLOY_FILE="/home/bxgh/microservice-stock/.last_deploy_commit"
if [ -f "$LAST_DEPLOY_FILE" ]; then
    LAST_COMMIT=$(cat $LAST_DEPLOY_FILE)
else
    LAST_COMMIT="HEAD~1"
fi

CURRENT_COMMIT=$(git rev-parse HEAD)
log "Comparing commits: $LAST_COMMIT -> $CURRENT_COMMIT"

# 获取变更的文件列表
CHANGED_FILES=$(git diff --name-only $LAST_COMMIT $CURRENT_COMMIT 2>/dev/null || git diff --name-only HEAD~1 HEAD)
log "Changed files:"
echo "$CHANGED_FILES" | tee -a $LOG_FILE

# 定义服务与路径的映射关系
declare -A SERVICE_PATHS
SERVICE_PATHS["mootdx-api"]="services/mootdx-api"
SERVICE_PATHS["mootdx-source"]="services/mootdx-source"
SERVICE_PATHS["gsd-worker"]="services/gsd-worker"
SERVICE_PATHS["task-orchestrator"]="services/task-orchestrator"
SERVICE_PATHS["get-stockdata"]="services/get-stockdata"
SERVICE_PATHS["quant-strategy"]="services/quant-strategy"
SERVICE_PATHS["intraday-tick-collector"]="services/get-stockdata"  # 使用相同镜像

# 共享库影响所有服务
SHARED_LIB="libs/gsd-shared"

# 判断哪些服务需要重建
SERVICES_TO_BUILD=""

# 检查共享库是否变化
if echo "$CHANGED_FILES" | grep -q "^$SHARED_LIB"; then
    log "Shared library changed - rebuilding ALL services"
    # 根据节点选择服务列表
    if [ "$CURRENT_IP" == "192.168.151.41" ]; then
        SERVICES_TO_BUILD="mootdx-api mootdx-source gsd-worker task-orchestrator get-stockdata quant-strategy intraday-tick-collector"
    else
        SERVICES_TO_BUILD="mootdx-api mootdx-source gsd-worker"
    fi
else
    # 逐个检查服务
    for SERVICE in "${!SERVICE_PATHS[@]}"; do
        PATH_PREFIX="${SERVICE_PATHS[$SERVICE]}"
        if echo "$CHANGED_FILES" | grep -q "^$PATH_PREFIX"; then
            log "Detected changes in $PATH_PREFIX -> Adding $SERVICE"
            SERVICES_TO_BUILD="$SERVICES_TO_BUILD $SERVICE"
        fi
    done
fi

# 去重并过滤非本节点服务
if [ "$CURRENT_IP" != "192.168.151.41" ]; then
    # 58/111 节点只保留 worker 相关服务
    SERVICES_TO_BUILD=$(echo "$SERVICES_TO_BUILD" | tr ' ' '\n' | grep -E "^(mootdx-api|mootdx-source|gsd-worker)$" | sort -u | tr '\n' ' ')
fi

# 去除空格
SERVICES_TO_BUILD=$(echo "$SERVICES_TO_BUILD" | xargs)

if [ -z "$SERVICES_TO_BUILD" ]; then
    log "No services need rebuilding. Deployment skipped."
else
    log "Services to rebuild: $SERVICES_TO_BUILD"
    docker compose -f $COMPOSE_FILE up -d --build $SERVICES_TO_BUILD
    log "Build and restart completed."
fi

# 记录本次部署的 commit
echo "$CURRENT_COMMIT" > $LAST_DEPLOY_FILE
log "Saved current commit: $CURRENT_COMMIT"

log "=== Smart Deploy Completed ==="
