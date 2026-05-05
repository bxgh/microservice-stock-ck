#!/bin/bash
# deploy_redis_cluster.sh
# 一键部署 3-Shard Redis 集群 (对标 ClickHouse 架构)
# Port: 16379 (Avoid conflict with host redis on 6379)

set -e

# Config
IMAGE="redis:7.0-alpine" 

# Helper function to remove protected files
clean_protected_dir() {
    local dir=$1
    if [ -d "$dir" ]; then
        echo "  Cleaning protected directory: $dir"
        docker run --rm -v "$dir:/data" $IMAGE sh -c 'rm -rf /data/*'
    fi
}

echo "===== 1. 停止并清理旧 Redis 集群 ====="

# 清理 Node 41
echo "Cleaning Node 41..."
docker rm -f microservice-stock-redis redis-cluster-node-41 redis-slave-node-41 2>/dev/null || true
clean_protected_dir "/home/bxgh/microservice-stock/infrastructure/redis/node-41/data"
rm -f infrastructure/redis/node-41/nodes.conf

# 清理 Node 58
echo "Cleaning Node 58..."
ssh bxgh@192.168.151.58 "docker rm -f microservice-stock-redis redis-cluster-node-58 redis-slave-node-58 2>/dev/null || true"
ssh bxgh@192.168.151.58 "docker run --rm -v /home/bxgh/microservice-stock/infrastructure/redis/node-58/data:/data $IMAGE sh -c 'rm -rf /data/*'"
ssh bxgh@192.168.151.58 "rm -f ~/microservice-stock/infrastructure/redis/node-58/nodes.conf"

# 清理 Node 111
echo "Cleaning Node 111..."
ssh bxgh@192.168.151.111 "docker rm -f microservice-stock-redis redis-cluster-node-111 redis-slave-node-111 2>/dev/null || true"
ssh bxgh@192.168.151.111 "docker run --rm -v /home/bxgh/microservice-stock/infrastructure/redis/node-111/data:/data $IMAGE sh -c 'rm -rf /data/*'"
ssh bxgh@192.168.151.111 "rm -f ~/microservice-stock/infrastructure/redis/node-111/nodes.conf"


echo ""
echo "===== 2. 分发新配置 (Port 16379) ====="

# Node 58
echo "Deploying to Node 58..."
ssh bxgh@192.168.151.58 "mkdir -p ~/microservice-stock/infrastructure/redis/node-58"
scp infrastructure/redis/node-58/docker-compose.yml bxgh@192.168.151.58:~/microservice-stock/infrastructure/redis/node-58/
scp infrastructure/redis/node-58/redis.conf bxgh@192.168.151.58:~/microservice-stock/infrastructure/redis/node-58/

# Node 111
echo "Deploying to Node 111..."
ssh bxgh@192.168.151.111 "mkdir -p ~/microservice-stock/infrastructure/redis/node-111"
scp infrastructure/redis/node-111/docker-compose.yml bxgh@192.168.151.111:~/microservice-stock/infrastructure/redis/node-111/
scp infrastructure/redis/node-111/redis.conf bxgh@192.168.151.111:~/microservice-stock/infrastructure/redis/node-111/


echo ""
echo "===== 3. 启动所有节点 ====="

# Node 41
echo "Starting Node 41..."
cd infrastructure/redis/node-41
docker compose up -d
cd ../../..

# Node 58
echo "Starting Node 58..."
ssh bxgh@192.168.151.58 "cd ~/microservice-stock/infrastructure/redis/node-58 && docker compose up -d"

# Node 111
echo "Starting Node 111..."
ssh bxgh@192.168.151.111 "cd ~/microservice-stock/infrastructure/redis/node-111 && docker compose up -d"

echo "Waiting 10s for nodes to be completely ready..."
sleep 10


echo ""
echo "===== 4. 创建 3-Shard 集群 ====="

echo "Creating cluster..."
# Try to create cluster on new ports
docker exec microservice-stock-redis redis-cli -p 16379 --cluster create \
  192.168.151.41:16379 \
  192.168.151.58:16379 \
  192.168.151.111:16379 \
  --cluster-replicas 0 \
  --cluster-yes

echo ""
echo "✅ Redis 3-Shard Cluster Deployed Successfully!"
echo "Check status:"
docker exec microservice-stock-redis redis-cli -p 16379 cluster nodes
