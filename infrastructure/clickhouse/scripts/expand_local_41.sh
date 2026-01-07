#!/bin/bash

# ClickHouse 3节点扩容 - 本地执行版（Server 41）
# 用途: 只更新当前服务器（41）的配置
# 使用方法: sudo bash expand_local_41.sh

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
echo -e "${CYAN}${BOLD}Server 41 配置更新（3节点模式）${NC}"
echo -e "${CYAN}${BOLD}========================================${NC}\n"

# 确认执行
echo -e "${YELLOW}此脚本将:${NC}"
echo -e "  1. 备份当前配置"
echo -e "  2. 更新为3节点配置"
echo -e "  3. 重启ClickHouse容器"
echo -e "  4. 验证启动成功"
echo -e ""
echo -e "${RED}${BOLD}⚠ 警告: 容器将重启约10-20秒${NC}\n"
read -p "$(echo -e ${CYAN}确认继续？[y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}操作已取消${NC}"
    exit 0
fi

START_TIME=$(date +%s)

# 步骤1: 备份
echo -e "\n${CYAN}[1/4] 创建配置备份${NC}"
mkdir -p "$BACKUP_DIR"
cp "$CONFIG_DIR"/keeper_config.xml "$BACKUP_DIR/" 2>/dev/null || true
cp "$CONFIG_DIR"/replication_config.xml "$BACKUP_DIR/" 2>/dev/null || true
echo -e "${GREEN}✓${NC} 备份已保存到: $BACKUP_DIR\n"

# 步骤2: 更新配置
echo -e "${CYAN}[2/4] 更新配置文件（3节点模式）${NC}"
cp "${CONFIG_DIR}/keeper_config_41_3nodes.xml" "${CONFIG_DIR}/keeper_config.xml"
cp "${CONFIG_DIR}/replication_config_41_3nodes.xml" "${CONFIG_DIR}/replication_config.xml"
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
    
    # 检查Keeper状态
    KEEPER_STATE=$(echo "mntr" | nc localhost 9181 2>/dev/null | grep "zk_server_state" | awk '{print $2}' || echo "unknown")
    echo -e "${GREEN}✓${NC} Keeper状态: ${BOLD}${KEEPER_STATE}${NC}"
    
    # 检查ClickHouse连接
    if docker exec $CONTAINER_NAME clickhouse-client --query "SELECT 1" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} ClickHouse客户端连接成功"
    else
        echo -e "${YELLOW}⚠${NC} ClickHouse客户端连接失败，请检查日志"
    fi
else
    echo -e "${RED}✗${NC} 容器启动失败"
    exit 1
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}${BOLD}✓ Server 41 更新完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "  耗时: ${DURATION} 秒"
echo -e "  备份: ${BACKUP_DIR}"
echo -e ""
echo -e "${CYAN}${BOLD}下一步操作:${NC}"
echo -e "  1. ${YELLOW}SSH到Server 111${NC}，执行相同操作"
echo -e "     ${BLUE}ssh root@192.168.151.111${NC}"
echo -e "     ${BLUE}cd /home/bxgh/microservice-stock${NC}"
echo -e "     ${BLUE}sudo bash infrastructure/clickhouse/scripts/expand_local_111.sh${NC}"
echo -e ""
echo -e "  2. ${YELLOW}SSH到Server 58${NC}（Leader，最后执行）"
echo -e "     ${BLUE}ssh root@192.168.151.58${NC}"
echo -e "     ${BLUE}cd /home/bxgh/microservice-stock${NC}"
echo -e "     ${BLUE}sudo bash infrastructure/clickhouse/scripts/expand_local_58.sh${NC}"
echo -e ""
echo -e "  3. 验证3节点集群"
echo -e "     ${BLUE}docker exec ${CONTAINER_NAME} clickhouse-client --query \"SELECT * FROM system.replicas LIMIT 3 FORMAT Vertical\"${NC}"
echo -e ""
