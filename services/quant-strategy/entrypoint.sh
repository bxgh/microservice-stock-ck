#!/bin/bash
# Smart entrypoint for Quant Strategy

echo "=========================================="
echo "Quant Strategy Service Starting..."
echo "=========================================="

# 1. Setup Runtime Proxy
if [ -n "$PROXY_URL" ]; then
    export HTTP_PROXY="$PROXY_URL"
    export HTTPS_PROXY="$PROXY_URL"
    export http_proxy="$PROXY_URL"
    export https_proxy="$PROXY_URL"
    # Basic no_proxy
    NO_PROXY="localhost,127.0.0.1"
    export NO_PROXY
    export no_proxy="$NO_PROXY"
    echo "✓ Proxy configured from env: $PROXY_URL"
else
    echo "⚠ No PROXY_URL set"
fi

# 2. Configure Proxychains (if enabled)
if [ "$ENABLE_PROXY_CHAINS" = "true" ] && [ -n "$PROXY_URL" ]; then
    echo "Configuring Proxychains..."
    # Extract host and port
    PROXY_HOST_PORT=$(echo "$PROXY_URL" | sed -e 's|^[^/]*//||' -e 's|/.*$||')
    PROXY_IP=$(echo "$PROXY_HOST_PORT" | cut -d: -f1)
    PROXY_PORT=$(echo "$PROXY_HOST_PORT" | cut -d: -f2)
    
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
    
    EXEC_CMD="proxychains4 -f /app/proxychains.conf"
    echo "✓ Execution will be wrapped with proxychains4"
else
    EXEC_CMD=""
fi

# 3. Start Application
echo "=========================================="
echo "Starting FastAPI application..."
echo "=========================================="
exec $EXEC_CMD "$@"
