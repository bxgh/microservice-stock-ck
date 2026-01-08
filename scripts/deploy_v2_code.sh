#!/bin/bash
set -e

# Build and distribute gsd-worker image for Architecture 2.0

echo "[1/4] Rebuilding gsd-worker image on Server 41..."
docker build -t gsd-worker:latest -f services/gsd-worker/Dockerfile .

echo "[2/4] Saving image to tarball..."
docker save gsd-worker:latest > /tmp/gsd-worker.tar

TARGET_IPS=("192.168.151.58" "192.168.151.111")

for IP in "${TARGET_IPS[@]}"; do
    echo "[3/4] Distributing to $IP..."
    scp /tmp/gsd-worker.tar bxgh@$IP:/tmp/
    
    echo "[4/4] Loading image on $IP..."
    ssh bxgh@$IP "docker load < /tmp/gsd-worker.tar"
done

echo "✅ Deployment complete across all nodes."
