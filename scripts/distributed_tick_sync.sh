#!/bin/bash
# 分布式分笔数据采集测试脚本
# 用途: 在 3 台服务器上并行执行分片采集

set -e

DATE=${1:-$(date +%Y%m%d)}
SCOPE=${2:-all}

echo "=== 分布式分笔采集测试 ==="
echo "日期: $DATE"
echo "范围: $SCOPE"
echo ""

# 服务器配置
SERVERS=("192.168.151.41" "192.168.151.58" "192.168.151.111")
SHARD_TOTAL=3

# 并行执行函数
run_worker() {
    local server=$1
    local shard_index=$2
    
    echo "[Shard $shard_index] 启动 @ $server"
    
    ssh bxgh@$server "cd /home/bxgh/microservice-stock && \
        docker run --rm --network host \
        -e SHARD_INDEX=$shard_index \
        -e SHARD_TOTAL=$SHARD_TOTAL \
        -e CLICKHOUSE_HOST=$server \
        -e CLICKHOUSE_PORT=9000 \
        -e MOOTDX_API_URL=http://$server:8003 \
        -v /home/bxgh/microservice-stock/services/gsd-worker/config:/app/config:ro \
        gsd-worker:latest \
        python -m jobs.sync_tick --scope $SCOPE --date $DATE \
        --shard-index $shard_index --shard-total $SHARD_TOTAL" \
    > /tmp/shard_${shard_index}.log 2>&1 &
    
    echo "[Shard $shard_index] PID: $!"
}

# 启动所有 worker
echo "启动 3 个分片 worker..."
for i in 0 1 2; do
    run_worker ${SERVERS[$i]} $i
done

# 等待所有任务完成
echo ""
echo "等待所有任务完成..."
wait

# 汇总结果
echo ""
echo "=== 采集完成 ==="
for i in 0 1 2; do
    echo "[Shard $i] 日志: /tmp/shard_${i}.log"
    grep -E "(成功|失败|耗时)" /tmp/shard_${i}.log | tail -5 || echo "  无结果"
done
