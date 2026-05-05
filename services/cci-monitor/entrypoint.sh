#!/bin/bash
set -e

echo "=========================================="
echo "CCI Monitor Service Starting..."
echo "=========================================="

# 配置运行时代理 (如果需要)
if [ -z "$HTTP_PROXY" ] && [ -n "$PROXY_URL" ]; then
    export HTTP_PROXY="$PROXY_URL"
    export HTTPS_PROXY="$PROXY_URL"
    export NO_PROXY="localhost,127.0.0.1"
    echo "✓ Proxy configured from PROXY_URL: $PROXY_URL"
fi

# 检查数据库连通性 (可选，这里先略过或用 nc 检查)
# while ! nc -z 127.0.0.1 36301; do
#   echo "Waiting for MySQL tunnel..."
#   sleep 1
# done

# 启动应用
echo "Starting FastAPI application on port 8085..."
exec "$@"
