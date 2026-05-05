#!/bin/bash
# 小规模分布式采集测试
# 用途: 测试分片逻辑，采集少量股票验证功能

set -e

DATE="20260107"
echo "=== 小规模分布式测试 (测试股票: 6只) ==="
echo "日期: $DATE"
echo ""

# 测试股票代码
TEST_STOCKS="000001,000002,000004,600000,600019,601318"

echo "测试股票: $TEST_STOCKS"
echo ""

# Server 41 - Shard 0
echo "[Shard 0 @ Server 41] 启动..."
docker run --rm --network host \
  -e SHARD_INDEX=0 \
  -e SHARD_TOTAL=3 \
  -e CLICKHOUSE_HOST=192.168.151.41 \
  -e CLICKHOUSE_PORT=9000 \
  -e MOOTDX_API_URL=http://192.168.151.41:8003 \
  gsd-worker:latest \
  jobs.sync_tick --scope all --date $DATE \
  --shard-index 0 --shard-total 3 2>&1 | tee /tmp/test_shard0.log &

# Server 58 - Shard 1
echo "[Shard 1 @ Server 58] 启动..."
ssh bxgh@192.168.151.58 "docker run --rm --network host \
  -e SHARD_INDEX=1 \
  -e SHARD_TOTAL=3 \
  -e CLICKHOUSE_HOST=192.168.151.58 \
  -e CLICKHOUSE_PORT=9000 \
  -e MOOTDX_API_URL=http://192.168.151.58:8003 \
  gsd-worker:latest \
  jobs.sync_tick --scope all --date $DATE \
  --shard-index 1 --shard-total 3 2>&1" | tee /tmp/test_shard1.log &

# Server 111 - Shard 2
echo "[Shard 2 @ Server 111] 启动..."
ssh bxgh@192.168.151.111 "docker run --rm --network host \
  -e SHARD_INDEX=2 \
  -e SHARD_TOTAL=3 \
  -e CLICKHOUSE_HOST=192.168.151.111 \
  -e CLICKHOUSE_PORT=9000 \
  -e MOOTDX_API_URL=http://192.168.151.111:8003 \
  gsd-worker:latest \
  jobs.sync_tick --scope all --date $DATE \
  --shard-index 2 --shard-total 3 2>&1" | tee /tmp/test_shard2.log &

echo ""
echo "等待所有任务完成..."
wait

echo ""
echo "=== 测试完成 ==="
echo "日志文件:"
echo "  - /tmp/test_shard0.log (Server 41)"
echo "  - /tmp/test_shard1.log (Server 58)"
echo "  - /tmp/test_shard2.log (Server 111)"
