#!/bin/bash
set -e

# Configs
NODE_41_IP="192.168.151.41"
NODE_58_IP="192.168.151.58"
NODE_111_IP="192.168.151.111"

echo "=== 1. Deploying Configs to Node 41 ==="
# Local is Node 41
cd /home/bxgh/microservice-stock/infrastructure/redis/node-41
docker compose up -d redis-slave-node-41

echo "=== 2. Deploying Configs to Node 58 ==="
ssh bxgh@${NODE_58_IP} "mkdir -p /home/bxgh/microservice-stock/infrastructure/redis/node-58/data-slave"
scp /home/bxgh/microservice-stock/infrastructure/redis/node-58/redis-slave.conf bxgh@${NODE_58_IP}:/home/bxgh/microservice-stock/infrastructure/redis/node-58/
scp /home/bxgh/microservice-stock/infrastructure/redis/node-58/docker-compose.yml bxgh@${NODE_58_IP}:/home/bxgh/microservice-stock/infrastructure/redis/node-58/
ssh bxgh@${NODE_58_IP} "cd /home/bxgh/microservice-stock/infrastructure/redis/node-58 && docker compose up -d redis-slave-node-58"

echo "=== 3. Deploying Configs to Node 111 ==="
ssh bxgh@${NODE_111_IP} "mkdir -p /home/bxgh/microservice-stock/infrastructure/redis/node-111/data-slave"
scp /home/bxgh/microservice-stock/infrastructure/redis/node-111/redis-slave.conf bxgh@${NODE_111_IP}:/home/bxgh/microservice-stock/infrastructure/redis/node-111/
scp /home/bxgh/microservice-stock/infrastructure/redis/node-111/docker-compose.yml bxgh@${NODE_111_IP}:/home/bxgh/microservice-stock/infrastructure/redis/node-111/
ssh bxgh@${NODE_111_IP} "cd /home/bxgh/microservice-stock/infrastructure/redis/node-111 && docker compose up -d redis-slave-node-111"

echo "✅ Deployment Complete. Slaves should be running on Port 6380."
