#!/bin/bash

# ClickHouse 3节点扩容 - Server 58配置更新
# 用途: 在58服务器上执行，更新为3节点配置（Leader最后执行）
# 使用方法: sudo bash expand_local_58.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_DIR="/home/bxgh/microservice-stock"
CONFIG_DIR="${PROJECT_DIR}/infrastructure/clickhouse/config"
BACKUP_DIR="/backup/clickhouse-expansion-$(date +%Y%m%d-%H%M%S)"
CONTAINER_NAME="microservice-stock-clickhouse"

echo -e "${CYAN}${BOLD}========================================${NC}"
echo -e "${CYAN}${BOLD}Server 58 配置更新（3节点模式）${NC}"
echo -e "${CYAN}${BOLD}========================================${NC}\n"

# 确认在58服务器上
CURRENT_IP=$(ip addr show | grep "inet 192.168" | grep -oP '192\.168\.\d+\.\d+' | head -1)
if [ "$CURRENT_IP" != "192.168.151.58" ]; then
    echo -e "${YELLOW}⚠ 警告: 当前IP是 $CURRENT_IP，不是 192.168.151.58${NC}"
    read -p "$(echo -e ${CYAN}确认继续？[y/N]: ${NC})" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# 确认是Leader
KEEPER_STATE=$(echo "mntr" | nc localhost 9181 2>/dev/null | grep "zk_server_state" | awk '{print $2}' || echo "unknown")
echo -e "当前Keeper状态: ${BOLD}${KEEPER_STATE}${NC}"
if [ "$KEEPER_STATE" = "leader" ]; then
    echo -e "${YELLOW}⚠ 这是Leader节点，应该最后更新${NC}\n"
fi

START_TIME=$(date +%s)

# 步骤1: 备份
echo -e "${CYAN}[1/4] 创建配置备份${NC}"
mkdir -p "$BACKUP_DIR"
cp "$CONFIG_DIR"/keeper_config.xml "$BACKUP_DIR/" 2>/dev/null || true
cp "$CONFIG_DIR"/replication_config.xml "$BACKUP_DIR/" 2>/dev/null || true
echo -e "${GREEN}✓${NC} 备份已保存到: $BACKUP_DIR\n"

# 步骤2: 更新配置
echo -e "${CYAN}[2/4] 更新配置文件（3节点模式）${NC}"
cp "${CONFIG_DIR}/keeper_config_58_3nodes.xml" "${CONFIG_DIR}/keeper_config.xml"
cp "${CONFIG_DIR}/replication_config_58_3nodes.xml" "${CONFIG_DIR}/replication_config.xml"
echo -e "${GREEN}✓${NC} 配置文件已更新\n"

# 步骤3: 重启容器
echo -e "${CYAN}[3/4] 重启ClickHouse容器${NC}"
echo -e "  停止容器..."
docker stop $CONTAINER_NAME >/dev/null 2>&1

echo -e "  启动容器..."
docker start $CONTAINER_NAME >/dev/null 2>&1

echo -e "  等待容器就绪..."
sleep 15

# 步骤4: 验证
echo -e "\n${CYAN}[4/4] 验证启动状态${NC}"

if docker ps | grep -q $CONTAINER_NAME; then
    echo -e "${GREEN}✓${NC} 容器运行中"
    
    KEEPER_STATE_NEW=$(echo "mntr" | nc localhost 9181 2>/dev/null | grep "zk_server_state" | awk '{print $2}' || echo "unknown")
    echo -e "${GREEN}✓${NC} Keeper状态: ${BOLD}${KEEPER_STATE_NEW}${NC}"
    
    if docker exec $CONTAINER_NAME clickhouse-client --query "SELECT 1" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} ClickHouse客户端连接成功"
    fi
else
    echo -e "${RED}✗${NC} 容器启动失败"
    exit 1
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}${BOLD}✓ Server 58 更新完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "  耗时: ${DURATION} 秒"
echo -e ""
echo -e "${CYAN}${BOLD}3节点扩容完成！${NC}"
echo -e "\n验证3节点集群:"
echo -e "  ${BLUE}docker exec ${CONTAINER_NAME} clickhouse-client --query \"SELECT database, table, total_replicas, active_replicas FROM system.replicas LIMIT 5 FORMAT Vertical\"${NC}\n"
