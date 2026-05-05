#!/bin/bash
# Start Architecture 2.0 Distributed Tick Acquisition

DATE=${1:-$(date +%Y%m%d)}
LOG_DIR="/home/bxgh/microservice-stock/logs/distributed_v2"
mkdir -p $LOG_DIR

echo "=== 启动架构 2.0 分布式采集 (Redis Cluster) ==="
echo "日期: $DATE"
echo "日志目录: $LOG_DIR"

# 0. 清理旧容器
echo "[0/3] 清理旧容器..."
docker rm -f gsd-worker-v2 2>/dev/null
ssh bxgh@192.168.151.58 "docker rm -f gsd-worker-v2" 2>/dev/null
ssh bxgh@192.168.151.111 "docker rm -f gsd-worker-v2" 2>/dev/null

# 1. 启动 Producer (派发任务)
echo "[1/3] 启动 Producer (Server 41)..."
docker run --rm --network host \
  -e MOOTDX_API_URL=http://localhost:8003 \
  -e REDIS_NODES="192.168.151.41:6379,192.168.151.58:6379,192.168.151.111:6379" \
  -e CLICKHOUSE_HOST=localhost \
  gsd-worker:latest \
  jobs.sync_tick --date $DATE --scope all \
  --distributed-source redis --distributed-role producer

if [ $? -ne 0 ]; then
    echo "❌ Producer 启动失败，终止任务"
    exit 1
fi

# 2. 启动 Consumers
echo "[2/3] 启动 Consumers..."

# Server 41
nohup docker run --name gsd-worker-v2 --network host \
  -e MOOTDX_API_URL=http://localhost:8003 \
  -e CLICKHOUSE_HOST=localhost \
  -e REDIS_NODES="192.168.151.41:6379,192.168.151.58:6379,192.168.151.111:6379" \
  -e HOSTNAME=server41 \
  -v $LOG_DIR:/app/logs \
  gsd-worker:latest \
  jobs.sync_tick --date $DATE --scope all \
  --distributed-source redis --distributed-role consumer \
  > $LOG_DIR/server41.log 2>&1 &

echo "  - Server 41 Consumer started"

# Server 58
ssh bxgh@192.168.151.58 "mkdir -p $LOG_DIR"
ssh bxgh@192.168.151.58 "nohup docker run --name gsd-worker-v2 --network host \
  -e MOOTDX_API_URL=http://192.168.151.41:8003 \
  -e CLICKHOUSE_HOST=localhost \
  -e REDIS_NODES='192.168.151.41:6379,192.168.151.58:6379,192.168.151.111:6379' \
  -e HOSTNAME=server58 \
  -v $LOG_DIR:/app/logs \
  gsd-worker:latest \
  jobs.sync_tick --date $DATE --scope all \
  --distributed-source redis --distributed-role consumer \
  > $LOG_DIR/server58.log 2>&1 &"

echo "  - Server 58 Consumer started"

# Server 111 (注意 ClickHouse IP 修正)
ssh bxgh@192.168.151.111 "mkdir -p $LOG_DIR"
ssh bxgh@192.168.151.111 "nohup docker run --name gsd-worker-v2 --network host \
  -e MOOTDX_API_URL=http://localhost:8003 \
  -e CLICKHOUSE_HOST=192.168.151.111 \
  -e REDIS_NODES='192.168.151.41:6379,192.168.151.58:6379,192.168.151.111:6379' \
  -e HOSTNAME=server111 \
  -v $LOG_DIR:/app/logs \
  gsd-worker:latest \
  jobs.sync_tick --date $DATE --scope all \
  --distributed-source redis --distributed-role consumer \
  > $LOG_DIR/server111.log 2>&1 &"

echo "  - Server 111 Consumer started"

echo "✅ 集群启动完成！请监控日志: tail -f $LOG_DIR/*.log"
