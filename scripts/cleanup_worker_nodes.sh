#!/bin/bash
# 清理 58/111 节点上不需要的容器
# 仅保留: clickhouse, mootdx-api, gitlab (仅58)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 需要停止的容器列表
CONTAINERS_TO_STOP=(
    "task-orchestrator"
    "quant-strategy-dev"
    "get-stockdata-api-dev"
    "microservice-stock-prometheus"
    "microservice-stock-rabbitmq"
    "microservice-stock-nacos"
    "microservice-stock-snapshot-recorder"
)

cleanup_node() {
    local node_ip=$1
    local node_name=$2
    
    echo -e "${YELLOW}=== 清理 $node_name ($node_ip) ===${NC}"
    
    for container in "${CONTAINERS_TO_STOP[@]}"; do
        if ssh -o ConnectTimeout=5 bxgh@$node_ip "docker ps -a --format '{{.Names}}' | grep -q '^${container}$'" 2>/dev/null; then
            echo -e "  ${RED}停止${NC}: $container"
            ssh bxgh@$node_ip "docker stop $container 2>/dev/null || true"
            ssh bxgh@$node_ip "docker rm $container 2>/dev/null || true"
        else
            echo -e "  ${GREEN}跳过${NC}: $container (不存在)"
        fi
    done
    
    echo -e "${GREEN}✓ $node_name 清理完成${NC}"
    echo ""
}

echo "================================================"
echo "  集群容器清理脚本"
echo "  58/111 节点仅保留必要服务"
echo "================================================"
echo ""

# 清理 Server 58
cleanup_node "192.168.151.58" "Server 58"

# 清理 Server 111
cleanup_node "192.168.151.111" "Server 111"

echo "================================================"
echo -e "${GREEN}清理完成！${NC}"
echo ""
echo "各节点剩余容器应为:"
echo "  Server 58:  clickhouse, mootdx-api, gitlab"
echo "  Server 111: clickhouse, mootdx-api"
echo ""
echo "验证命令:"
echo "  ssh bxgh@192.168.151.58 'docker ps'"
echo "  ssh bxgh@192.168.151.111 'docker ps'"
echo "================================================"
