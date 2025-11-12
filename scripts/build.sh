#!/bin/bash

# microservice-stock 构建脚本

set -e

echo "🔨 构建 microservice-stock 项目..."

# 构建 TaskScheduler 服务
echo "🐍 构建 TaskScheduler 服务..."
cd services/task-scheduler
docker build -t microservice-stock/task-scheduler:latest .
cd ../..

# 构建 Web UI (如果存在 package.json)
if [ -f services/web-ui/package.json ]; then
    echo "⚛️ 构建 Web UI..."
    cd services/web-ui
    npm install
    npm run build
    docker build -t microservice-stock/web-ui:latest .
    cd ../..
fi

# 构建其他 Python 服务
services=("data-collector" "data-processor" "data-storage" "notification" "monitor")

for service in "${services[@]}"; do
    if [ -f "services/$service/requirements.txt" ]; then
        echo "🐍 构建 $service 服务..."
        cd services/$service
        docker build -t microservice-stock/$service:latest .
        cd ../..
    fi
done

echo "✅ 构建完成！"
echo ""
echo "📋 构建的镜像："
docker images | grep microservice-stock