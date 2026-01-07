#!/bin/bash
# 3节点集群状态检查脚本

echo "========================================="
echo "ClickHouse 3节点集群状态报告"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="
echo ""

echo "[1] Keeper集群状态"
echo "-------------------"
echo -n "Server 41 (192.168.151.41): "
echo 'mntr' | nc localhost 9181 2>/dev/null | grep zk_server_state | awk '{print $2}' || echo "未响应"

echo -n "Server 58 (192.168.151.58): "
ssh -o ConnectTimeout=3 bxgh@192.168.151.58 "echo 'mntr' | nc localhost 9181 2>/dev/null | grep zk_server_state | awk '{print \$2}'" 2>/dev/null || echo "未响应"

echo -n "Server 111 (192.168.151.111): "
ssh -o ConnectTimeout=3 bxgh@192.168.151.111 "echo 'mntr' | nc localhost 9181 2>/dev/null | grep zk_server_state | awk '{print \$2}'" 2>/dev/null || echo "未响应"

echo ""
echo "[2] 副本状态"
echo "-------------------"
docker exec microservice-stock-clickhouse clickhouse-client --query "
SELECT 
    '总副本数' as metric, max(total_replicas) as value FROM system.replicas
UNION ALL
SELECT '在线副本数' as metric, max(active_replicas) as value FROM system.replicas
UNION ALL
SELECT '只读表数' as metric, sum(is_readonly) as value FROM system.replicas
UNION ALL
SELECT '同步队列' as metric, sum(queue_size) as value FROM system.replicas
FORMAT TSV
" 2>/dev/null | while IFS=$'\t' read metric value; do
    printf "%-15s: %s\n" "$metric" "$value"
done

echo ""
echo "[3] 示例复制表"
echo "-------------------"
docker exec microservice-stock-clickhouse clickhouse-client --query "
SELECT database, table, total_replicas, active_replicas, is_readonly
FROM system.replicas
LIMIT 3
FORMAT Pretty
" 2>/dev/null

echo ""
echo "========================================="
if docker exec microservice-stock-clickhouse clickhouse-client --query "SELECT max(total_replicas) FROM system.replicas" 2>/dev/null | grep -q "3"; then
    echo "✓ 3节点集群配置成功！"
else
    echo "⚠ 集群可能还在同步中，请等待几分钟..."
fi
echo "========================================="
