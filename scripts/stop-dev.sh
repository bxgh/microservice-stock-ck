#!/bin/bash

# microservice-stock 开发环境停止脚本

set -e

echo "🛑 停止 microservice-stock 开发环境..."

# 停止所有服务
echo "⏹️ 停止所有 Docker Compose 服务..."
docker-compose down

# 可选：清理相关容器和镜像
read -p "是否要清理相关的 Docker 镜像？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 清理 Docker 镜像..."
    docker-compose down --rmi all
fi

# 可选：清理卷
read -p "是否要清理数据卷（注意：这会删除所有数据）？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 清理数据卷..."
    docker-compose down -v
fi

echo "✅ 开发环境已停止"

# 显示容器状态
echo ""
echo "📋 当前容器状态："
docker ps -a --filter "name=microservice-stock" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"