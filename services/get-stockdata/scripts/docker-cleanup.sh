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

# 清理未使用的镜像（保留最近7天的镜像）
log "清理7天前未使用的镜像..."
docker image prune -a -f --filter "until=168h" >> "$LOG_FILE" 2>&1

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