#!/bin/bash

# Docker 定时清理脚本
# 用于清理未使用的 Docker 资源

# 设置日志文件路径
LOG_FILE="$HOME/docker-cleanup.log"

# 记录日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 开始清理
log "开始 Docker 清理任务"

# 清理未使用的容器
log "清理未使用的容器..."
docker container prune -f >> "$LOG_FILE" 2>&1

# 清理未使用的镜像（保留最近7天的镜像，但排除核心业务镜像）
log "清理7天前未使用的镜像 (排除核心镜像)..."
# 获取核心镜像列表（按需添加）
EXCLUDE_IMAGES=("gsd-worker" "task-orchestrator" "gsd-api" "get-stockdata" "quant-strategy" "mootdx-api" "mootdx-source")

# 重新标记核心镜像以重置其 'Last Used/Created' 状态并非易事，
# 但可以通过 docker image prune 的 --filter label 或类似方式处理。
# 这里的简单方案是：只在镜像不属于核心列表时才清理，或者干脆只清理 dangling 镜像。
# 考虑到稳定性，我们将 -a 改为只清理无标签镜像，或者在 prune 后确保核心镜像存在（但这不现实）。
# 更好的做法是：使用 scripts/cleanup_docker.sh 中已经实现的逻辑。

# 为保持简单且有效，我们修改为：
# 1. 先清理所有 dangling 镜像
docker image prune -f >> "$LOG_FILE" 2>&1
# 2. 对于超过 7 天的镜像，我们只清理那些不在白名单里的
# 注意：docker image prune --filter 不支持 "label!=..." 这种反向过滤很好用，但如果没有 label 就很难。
# 所以我们采用：如果是这些核心镜像，我们不进行 -a 清理。
log "由于春节等长假，核心镜像可能超过7天未运行。改为仅清理无标签镜像，以保安全。"
# docker image prune -a -f --filter "until=168h" >> "$LOG_FILE" 2>&1 # 这一行是导致问题的根源

# 清理未使用的网络
log "清理未使用的网络..."
docker network prune -f >> "$LOG_FILE" 2>&1

# 清理未使用的卷（谨慎使用，会删除重要数据）
# 如果需要清理卷，请取消下面的注释
# log "清理未使用的卷..."
# docker volume prune -f >> "$LOG_FILE" 2>&1

# 显示系统空间使用情况
log "当前 Docker 系统空间使用情况："
docker system df >> "$LOG_FILE" 2>&1

log "Docker 清理任务完成"

# 发送清理完成通知（可选）
# 可以在这里添加邮件或其他通知方式