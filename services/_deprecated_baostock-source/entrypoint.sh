#!/bin/bash
# Baostock Source Entrypoint

echo "=========================================="
echo "Baostock Source Service Starting..."
echo "=========================================="

# Configure Proxychains for Baostock (Required for Port 10030)
# Default to host IP bridge if not set: 192.168.151.41:8900
PROXY_HOST=${PROXY_HOST:-192.168.151.41}
PROXY_PORT=${PROXY_PORT:-8900}

echo "Configuring Proxychains for SOCKS5 bridge at $PROXY_HOST:$PROXY_PORT..."

cat > /etc/proxychains4.conf <<EOF
strict_chain
proxy_dns 
remote_dns_subnet 224
tcp_read_time_out 15000
tcp_connect_time_out 8000
localnet 127.0.0.0/255.0.0.0
localnet 192.168.0.0/255.255.0.0
[ProxyList]
socks5 $PROXY_HOST $PROXY_PORT
EOF

echo "✓ Proxychains configured"

# Set execute command to wrap python with proxychains4
# This ensures ALL network traffic from the python process goes through the SOCKS5 proxy
EXEC_CMD="proxychains4 -f /etc/proxychains4.conf"

# 3. Start Application
echo "=========================================="
echo "Starting gRPC service wrapped in Proxychains..."
echo "=========================================="
exec $EXEC_CMD "$@"
