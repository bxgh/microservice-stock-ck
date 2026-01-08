#!/bin/bash
# 3节点分布式分笔采集测试
# 日期: 2026-01-07
# 范围: 全市场（约5300只）

set -e

DATE="20260107"
echo "=== 3节点分布式全市场采集测试 ==="
echo "日期: $DATE"
echo "预估耗时: 25-30 分钟"
echo ""

START_TIME=$(date +%s)

# 并行启动3个节点
echo "[$(date +%H:%M:%S)] 启动 Shard 0 @ Server 41..."
docker run --rm --network host \
  -e SHARD_INDEX=0 \
  -e SHARD_TOTAL=3 \
  -e CLICKHOUSE_HOST=192.168.151.41 \
  -e MOOTDX_API_URL=http://192.168.151.41:8003 \
  gsd-worker:latest \
  jobs.sync_tick --scope all --date $DATE \
  --shard-index 0 --shard-total 3 2>&1 | tee /tmp/dist_shard0.log &
PID0=$!

echo "[$(date +%H:%M:%S)] 启动 Shard 1 @ Server 58..."
ssh bxgh@192.168.151.58 "docker run --rm --network host \
  -e SHARD_INDEX=1 \
  -e SHARD_TOTAL=3 \
  -e CLICKHOUSE_HOST=192.168.151.58 \
  -e MOOTDX_API_URL=http://192.168.151.58:8003 \
  gsd-worker:latest \
  jobs.sync_tick --scope all --date $DATE \
  --shard-index 1 --shard-total 3" 2>&1 | tee /tmp/dist_shard1.log &
PID1=$!

echo "[$(date +%H:%M:%S)] 启动 Shard 2 @ Server 111..."
ssh bxgh@192.168.151.111 "docker run --rm --network host \
  -e SHARD_INDEX=2 \
  -e SHARD_TOTAL=3 \
  -e CLICKHOUSE_HOST=192.168.151.111 \
  -e MOOTDX_API_URL=http://192.168.151.111:8003 \
  gsd-worker:latest \
  jobs.sync_tick --scope all --date $DATE \
  --shard-index 2 --shard-total 3" 2>&1 | tee /tmp/dist_shard2.log &
PID2=$!

echo ""
echo "正在采集... PIDs: $PID0, $PID1, $PID2"
echo ""

# 等待所有任务完成
wait $PID0
wait $PID1
wait $PID2

# 计算耗时
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo "=== 采集完成 ==="
echo "总耗时: ${MINUTES}分${SECONDS}秒"
echo ""

# 提取关键信息
echo "=== 各节点统计 ==="
for i in 0 1 2; do
    echo ""
    echo "Shard $i:"
    grep -E "(分片过滤|待采集|成功|失败|耗时)" /tmp/dist_shard${i}.log | tail -5 || echo "  无数据"
done
