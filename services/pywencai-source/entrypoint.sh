#!/bin/bash
# Pywencai Source Entrypoint

echo "=========================================="
echo "Pywencai Source Service Starting..."
echo "=========================================="

# 1. 设置运行时代理
if [ -n "$PROXY_URL" ]; then
    export HTTP_PROXY="$PROXY_URL"
    export HTTPS_PROXY="$PROXY_URL"
    export http_proxy="$PROXY_URL"
    export https_proxy="$PROXY_URL"
    # Pywencai needs proxy for www.iwencai.com
    NO_PROXY="localhost,127.0.0.1"
    export NO_PROXY
    export no_proxy="$NO_PROXY"
    echo "✓ Proxy configured: $PROXY_URL"
else
    echo "⚠ No PROXY_URL set"
    unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy NO_PROXY no_proxy
fi

# 2. Configure Proxychains (if enabled)
if [ "$ENABLE_PROXY_CHAINS" = "true" ] && [ -n "$PROXY_URL" ]; then
    echo "Configuring Proxychains..."
    
    # Extract host and port
    PROXY_HOST_PORT=$(echo "$PROXY_URL" | sed -e 's|^[^/]*//||' -e 's|/.*$||')
    PROXY_IP=$(echo "$PROXY_HOST_PORT" | cut -d: -f1)
    PROXY_PORT=$(echo "$PROXY_HOST_PORT" | cut -d: -f2)
    
    # Create config
    cat > /app/proxychains.conf <<EOF
strict_chain
proxy_dns 
remote_dns_subnet 224
tcp_read_time_out 15000
tcp_connect_time_out 8000
localnet 127.0.0.0/255.0.0.0
localnet 192.168.0.0/255.255.0.0
[ProxyList]
http $PROXY_IP $PROXY_PORT
EOF
    echo "✓ Proxychains configured"
    
    EXEC_CMD="proxychains4 -f /app/proxychains.conf"
else
    EXEC_CMD=""
fi

# 3. 启动应用
echo "=========================================="
echo "Starting gRPC service..."
echo "=========================================="
exec $EXEC_CMD "$@"
