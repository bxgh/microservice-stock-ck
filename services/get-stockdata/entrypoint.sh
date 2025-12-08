#!/bin/bash
# 智能启动脚本 - 确保所有数据源就绪

echo "=========================================="
echo "Get-StockData Service Starting..."
echo "=========================================="

# 1. 设置运行时代理
if [ -n "$PROXY_URL" ]; then
    export HTTP_PROXY="$PROXY_URL"
    export HTTPS_PROXY="$PROXY_URL"
    export http_proxy="$PROXY_URL"
    export https_proxy="$PROXY_URL"
    # Akshare needs proxy, but internal/Mootdx might not
    NO_PROXY="localhost,127.0.0.1,hq.sinajs.cn,qt.gtimg.cn,www.iwencai.com"
    export NO_PROXY
    export no_proxy="$NO_PROXY"
    echo "✓ Proxy configured from env: $PROXY_URL"
    echo "✓ NO_PROXY configured: $NO_PROXY"
else
    echo "⚠ No PROXY_URL set, ensuring no proxy env vars remain"
    unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy NO_PROXY no_proxy
fi

# 2. 初始化 Mootdx - 发现最优服务器
echo "Initializing Mootdx..."
if python3 -m mootdx bestip 2>&1 | grep -q "已经将最优服务器"; then
    echo "✓ Mootdx bestip completed"
else
    echo "⚠ Mootdx bestip failed (will retry on demand)"
fi

# 3. 启动应用
echo "=========================================="
echo "Starting FastAPI application..."
echo "=========================================="
exec "$@"
