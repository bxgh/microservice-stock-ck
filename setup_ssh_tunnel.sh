#!/bin/bash

# SSH Dynamic SOCKS5 Proxy
# Local Port: 1080
# Jump Host: Server 111 (192.168.151.111)

LOCAL_SOCKS_PORT=1080
JUMP_HOST=192.168.151.111
JUMP_USER=bxgh

echo "Setting up SSH Dynamic SOCKS5 Proxy: 127.0.0.1:$LOCAL_SOCKS_PORT -> $JUMP_HOST"

# Kill existing process on this port
PID=$(lsof -t -i:$LOCAL_SOCKS_PORT)
if [ ! -z "$PID" ]; then
    echo "Killing existing process on port $LOCAL_SOCKS_PORT (PID: $PID)"
    kill -9 $PID
fi

# Start SSH Tunnel with Dynamic Forwarding (-D)
ssh -f -N \
    -o BatchMode=yes \
    -o ConnectTimeout=10 \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    -o StrictHostKeyChecking=no \
    -D 0.0.0.0:$LOCAL_SOCKS_PORT \
    $JUMP_USER@$JUMP_HOST

if [ $? -eq 0 ]; then
    echo "SOCKS5 Tunnel started successfully on port $LOCAL_SOCKS_PORT."
    echo "Testing connectivity..."
    sleep 2
    nc -zv 127.0.0.1 $LOCAL_SOCKS_PORT
else
    echo "Failed to start SSH tunnel."
    exit 1
fi
