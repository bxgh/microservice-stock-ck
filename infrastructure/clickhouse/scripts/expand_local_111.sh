#!/bin/bash

# ClickHouse 3节点扩容 - Server 111配置部署
# 用途: 在111服务器上执行，部署3节点配置
# 使用方法: sudo bash expand_local_111.sh

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
echo -e "${CYAN}${BOLD}Server 111 配置部署（3节点模式）${NC}"
echo -e "${CYAN}${BOLD}========================================${NC}\n"

# 确认在111服务器上
CURRENT_IP=$(ip addr show | grep "inet 192.168" | grep -oP '192\.168\.\d+\.\d+' | head -1)
if [ "$CURRENT_IP" != "192.168.151.111" ]; then
    echo -e "${YELLOW}⚠ 警告: 当前IP是 $CURRENT_IP，不是 192.168.151.111${NC}"
    read -p "$(echo -e ${CYAN}确认继续？[y/N]: ${NC})" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

START_TIME=$(date +%s)

# 步骤1: 备份
echo -e "\n${CYAN}[1/4] 创建配置备份${NC}"
mkdir -p "$BACKUP_DIR"
cp "$CONFIG_DIR"/keeper_config.xml "$BACKUP_DIR/" 2>/dev/null || true
cp "$CONFIG_DIR"/replication_config.xml "$BACKUP_DIR/" 2>/dev/null || true
echo -e "${GREEN}✓${NC} 备份已保存到: $BACKUP_DIR\n"

# 步骤2: 部署配置
echo -e "${CYAN}[2/4] 部署111配置文件${NC}"
cp "${CONFIG_DIR}/keeper_config_111.xml" "${CONFIG_DIR}/keeper_config.xml"
cp "${CONFIG_DIR}/replication_config_111.xml" "${CONFIG_DIR}/replication_config.xml"
echo -e "${GREEN}✓${NC} 配置文件已部署（server_id=3, replica=server111）\n"

# 步骤3: 重启容器
echo -e "${CYAN}[3/4] 重启ClickHouse容器${NC}"
echo -e "  停止容器..."
docker stop $CONTAINER_NAME >/dev/null 2>&1 || true

echo -e "  启动容器..."
docker start $CONTAINER_NAME >/dev/null 2>&1

echo -e "  等待容器就绪..."
sleep 15

# 步骤4: 验证
echo -e "\n${CYAN}[4/4] 验证启动状态${NC}"

if docker ps | grep -q $CONTAINER_NAME; then
    echo -e "${GREEN}✓${NC} 容器运行中"
    
    KEEPER_STATE=$(echo "mntr" | nc localhost 9181 2>/dev/null | grep "zk_server_state" | awk '{print $2}' || echo "unknown")
    echo -e "${GREEN}✓${NC} Keeper状态: ${BOLD}${KEEPER_STATE}${NC}"
    
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
echo -e "${GREEN}${BOLD}✓ Server 111 部署完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "  耗时: ${DURATION} 秒"
echo -e ""
echo -e "${CYAN}${BOLD}下一步:${NC} 在Server 58上执行最后的更新${NC}"
echo -e "  ${BLUE}ssh root@192.168.151.58${NC}"
echo -e "  ${BLUE}cd /home/bxgh/microservice-stock${NC}"
echo -e "  ${BLUE}sudo bash infrastructure/clickhouse/scripts/expand_local_58.sh${NC}\n"
