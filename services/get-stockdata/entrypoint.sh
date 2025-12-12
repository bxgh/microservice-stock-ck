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
# 2.5 Configure Proxychains (if enabled)
if [ "$ENABLE_PROXY_CHAINS" = "true" ] && [ -n "$PROXY_URL" ]; then
    echo "Configuring Proxychains..."
    
    # Validate PROXY_URL format
    if ! echo "$PROXY_URL" | grep -qE '^https?://[^:]+:[0-9]+$'; then
        echo "❌ Error: Invalid PROXY_URL format: $PROXY_URL"
        echo "   Expected format: http://host:port or https://host:port"
        exit 1
    fi
    
    # Extract host and port from http://host:port or https://host:port
    PROXY_HOST_PORT=$(echo "$PROXY_URL" | sed -e 's|^[^/]*//||' -e 's|/.*$||')
    PROXY_IP=$(echo "$PROXY_HOST_PORT" | cut -d: -f1)
    PROXY_PORT=$(echo "$PROXY_HOST_PORT" | cut -d: -f2)
    
    # Validate IP address format
    if ! echo "$PROXY_IP" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
        echo "❌ Error: Invalid IP address: $PROXY_IP"
        exit 1
    fi
    
    # Validate port number range
    if ! [ "$PROXY_PORT" -ge 1 ] 2>/dev/null || ! [ "$PROXY_PORT" -le 65535 ] 2>/dev/null; then
        echo "❌ Error: Invalid port number: $PROXY_PORT (must be 1-65535)"
        exit 1
    fi
    
    # Create custom config
    cat > /app/proxychains.conf <<EOF
strict_chain
proxy_dns 
remote_dns_subnet 224
tcp_read_time_out 15000
tcp_connect_time_out 8000
[ProxyList]
http $PROXY_IP $PROXY_PORT
EOF
    echo "✓ Proxychains config created at /app/proxychains.conf"
    
    # Wrap execution with proxychains
    EXEC_CMD="proxychains4 -f /app/proxychains.conf"
    echo "✓ Execution will be wrapped with proxychains4"
else
    EXEC_CMD=""
fi

# 3. 启动应用
echo "=========================================="
echo "Starting FastAPI application..."
echo "=========================================="
exec $EXEC_CMD "$@"
