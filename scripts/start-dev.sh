#!/bin/bash

# microservice-stock 开发环境启动脚本

set -e

echo "🚀 启动 microservice-stock 开发环境..."

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "❌ 未找到 .env 文件，请先复制 .env.example 并配置环境变量"
    exit 1
fi

# 启动基础设施服务
echo "📦 启动基础设施服务 (Redis, ClickHouse)..."
docker-compose -f infrastructure/docker-compose.yml up -d redis clickhouse

# 等待服务就绪
echo "⏳ 等待服务就绪..."
sleep 10

# 检查 Redis 连接
echo "🔍 检查 Redis 连接..."
if ! docker exec microservice-stock-redis redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis 连接失败"
    exit 1
fi

# 检查 ClickHouse 连接
echo "🔍 检查 ClickHouse 连接..."
if ! curl -s http://localhost:8123/ping > /dev/null 2>&1; then
    echo "❌ ClickHouse 连接失败"
    exit 1
fi

echo "✅ 基础设施服务启动成功"

# 启动应用服务
echo "🏗️ 启动应用服务..."
docker-compose up -d task-scheduler

# 检查应用服务
echo "🔍 检查应用服务健康状态..."
sleep 5
if ! curl -s http://localhost:8080/api/v1/health > /dev/null 2>&1; then
    echo "⚠️ 应用服务可能还在启动中，请稍等..."
fi

echo "🎉 开发环境启动完成！"
echo ""
echo "📋 服务地址："
echo "   - Redis: localhost:6379"
echo "   - ClickHouse: localhost:8123"
echo "   - TaskScheduler API: http://localhost:8080"
echo "   - API文档: http://localhost:8080/docs"
echo ""
echo "💡 使用 './scripts/start-dev.sh --all' 启动所有服务（包括 Web UI）"
echo "💡 使用 './scripts/stop-dev.sh' 停止开发环境"