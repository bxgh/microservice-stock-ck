#!/bin/bash
# sync_images_to_nodes.sh
# 既然远程节点无法联网拉取镜像，我们就手动分发

set -e

IMAGE="redis:7.0-alpine"
TAR_FILE="/tmp/redis_7.0_alpine.tar"

echo "=== 1. Saving Image on Local (Node 41) ==="
# Ensure we have it
docker pull $IMAGE
echo "Saving $IMAGE to $TAR_FILE..."
docker save -o $TAR_FILE $IMAGE

echo "=== 2. Distributing to Node 58 ==="
scp $TAR_FILE bxgh@192.168.151.58:$TAR_FILE
echo "Loading image on Node 58..."
ssh bxgh@192.168.151.58 "docker load -i $TAR_FILE"

echo "=== 3. Distributing to Node 111 ==="
scp $TAR_FILE bxgh@192.168.151.111:$TAR_FILE
echo "Loading image on Node 111..."
ssh bxgh@192.168.151.111 "docker load -i $TAR_FILE"

echo "✅ Image Sync Complete!"
echo "Cleaning up local tar..."
rm $TAR_FILE
