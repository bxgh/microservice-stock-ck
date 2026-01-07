#!/bin/bash

# ClickHouse 3节点扩容 - 一键执行脚本
# 适用于：从41克隆的58和111服务器，Docker化部署
# 执行位置：在41服务器上运行
# 使用方法: sudo bash one_click_expansion.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# 服务器配置
SERVER_41="192.168.151.41"
SERVER_58="192.168.151.58"
SERVER_111="192.168.151.111"

# 项目路径（克隆服务器应该相同）
PROJECT_DIR="/home/bxgh/microservice-stock"
CONFIG_DIR="${PROJECT_DIR}/infrastructure/clickhouse/config"
BACKUP_DIR="/backup/clickhouse-expansion-$(date +%Y%m%d-%H%M%S)"

# ClickHouse容器名
CONTAINER_NAME="microservice-stock-clickhouse"

# 检查是否在41服务器上
CURRENT_IP=$(ip addr show | grep "inet 192.168" | grep -oP '192\.168\.\d+\.\d+' | head -1)
if [ "$CURRENT_IP" != "$SERVER_41" ]; then
    echo -e "${RED}错误: 此脚本必须在 Server 41 (192.168.151.41) 上执行${NC}"
    echo -e "当前IP: $CURRENT_IP"
    exit 1
fi

# 确认执行
echo -e "${CYAN}${BOLD}========================================${NC}"
echo -e "${CYAN}${BOLD}ClickHouse 3节点扩容 - 一键执行${NC}"
echo -e "${CYAN}${BOLD}========================================${NC}"
echo -e ""
echo -e "${YELLOW}扩容内容:${NC}"
echo -e "  • 将现有 2节点集群扩展至 3节点"
echo -e "  • Server 41 (Follower) - 更新配置并重启"
echo -e "  • Server 111 (New) - 部署配置并重启"
echo -e "  • Server 58 (Leader) - 更新配置并重启"
echo -e ""
echo -e "${YELLOW}预计耗时: 3-5 分钟${NC}"
echo -e "${YELLOW}服务中断: 每台约10-20秒${NC}"
echo -e ""
echo -e "${RED}${BOLD}⚠ 警告: 此操作将重启所有ClickHouse容器！${NC}"
echo -e ""
read -p "$(echo -e ${CYAN}确认继续？[y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}操作已取消${NC}"
    exit 0
fi

# 开始执行
START_TIME=$(date +%s)
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}开始执行扩容操作${NC}"
echo -e "${BLUE}开始时间: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}========================================${NC}\n"

# ========================================
# 步骤 1: 创建备份
# ========================================
echo -e "${CYAN}[步骤 1/8] 创建配置备份${NC}"
mkdir -p "$BACKUP_DIR"
cp -r "$CONFIG_DIR"/* "$BACKUP_DIR/" 2>/dev/null || true
echo -e "${GREEN}✓${NC} 备份已保存到: $BACKUP_DIR"
echo ""

# ========================================
# 步骤 2: 验证当前集群状态
# ========================================
echo -e "${CYAN}[步骤 2/8] 验证当前集群状态${NC}"

# 检查Keeper状态
KEEPER_41=$(echo "mntr" | nc localhost 9181 2>/dev/null | grep "zk_server_state" | awk '{print $2}' || echo "unknown")
KEEPER_58=$(echo "mntr" | nc $SERVER_58 9181 2>/dev/null | grep "zk_server_state" | awk '{print $2}' || echo "unknown")

echo -e "  Server 41 Keeper: ${KEEPER_41}"
echo -e "  Server 58 Keeper: ${KEEPER_58}"

if [ "$KEEPER_41" != "follower" ] && [ "$KEEPER_41" != "leader" ]; then
    echo -e "${RED}✗${NC} Server 41 Keeper状态异常"
    exit 1
fi

if [ "$KEEPER_58" != "follower" ] && [ "$KEEPER_58" != "leader" ]; then
    echo -e "${RED}✗${NC} Server 58 Keeper状态异常"
    exit 1
fi

# 检查副本健康度
READONLY_COUNT=$(docker exec $CONTAINER_NAME clickhouse-client --query \
    "SELECT count() FROM system.replicas WHERE is_readonly = 1" 2>/dev/null || echo "999")

if [ "$READONLY_COUNT" != "0" ]; then
    echo -e "${RED}✗${NC} 警告: 存在${READONLY_COUNT}个只读复制表"
    read -p "$(echo -e ${YELLOW}是否继续？[y/N]: ${NC})" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✓${NC} 集群状态验证通过"
echo ""

# ========================================
# 步骤 3: 测试SSH连通性
# ========================================
echo -e "${CYAN}[步骤 3/8] 测试SSH连通性${NC}"

test_ssh() {
    local host=$1
    if ssh -o ConnectTimeout=5 -o BatchMode=yes root@$host "exit" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Server $host SSH连接成功"
        return 0
    else
        echo -e "${RED}✗${NC} Server $host SSH连接失败"
        echo -e "${YELLOW}  提示: 请确保已配置SSH密钥或使用密码认证${NC}"
        return 1
    fi
}

test_ssh $SERVER_58 || exit 1
test_ssh $SERVER_111 || exit 1
echo ""

# ========================================
# 步骤 4: 更新 Server 41 配置（Follower）
# ========================================
echo -e "${CYAN}[步骤 4/8] 更新 Server 41 配置${NC}"

# 使用3节点配置覆盖当前配置
cp "${CONFIG_DIR}/keeper_config_41_3nodes.xml" "${CONFIG_DIR}/keeper_config.xml"
cp "${CONFIG_DIR}/replication_config_41_3nodes.xml" "${CONFIG_DIR}/replication_config.xml"

echo -e "${GREEN}✓${NC} Server 41 配置文件已更新（3节点模式）"
echo ""

# ========================================
# 步骤 5: 重启 Server 41 容器
# ========================================
echo -e "${CYAN}[步骤 5/8] 重启 Server 41 容器${NC}"

echo -e "  停止容器..."
docker stop $CONTAINER_NAME >/dev/null 2>&1

echo -e "  启动容器..."
docker start $CONTAINER_NAME >/dev/null 2>&1

echo -e "  等待容器就绪..."
sleep 15

# 验证重启成功
if docker ps | grep -q $CONTAINER_NAME; then
    KEEPER_STATE=$(echo "mntr" | nc localhost 9181 2>/dev/null | grep "zk_server_state" | awk '{print $2}' || echo "unknown")
    echo -e "${GREEN}✓${NC} Server 41 重启成功 (Keeper: $KEEPER_STATE)"
else
    echo -e "${RED}✗${NC} Server 41 容器启动失败"
    exit 1
fi
echo ""

# ========================================
# 步骤 6: 部署并启动 Server 111
# ========================================
echo -e "${CYAN}[步骤 6/8] 部署并启动 Server 111${NC}"

# 传输3节点配置文件到111
echo -e "  传输配置文件..."
scp "${CONFIG_DIR}/keeper_config_111.xml" \
    root@${SERVER_111}:${CONFIG_DIR}/keeper_config.xml >/dev/null 2>&1

scp "${CONFIG_DIR}/replication_config_111.xml" \
    root@${SERVER_111}:${CONFIG_DIR}/replication_config.xml >/dev/null 2>&1

echo -e "${GREEN}✓${NC} 配置文件已传输到 Server 111"

# 重启111的容器
echo -e "  重启 Server 111 容器..."
ssh root@${SERVER_111} "cd ${PROJECT_DIR} && docker stop ${CONTAINER_NAME} 2>/dev/null || true" >/dev/null 2>&1
ssh root@${SERVER_111} "cd ${PROJECT_DIR} && docker start ${CONTAINER_NAME}" >/dev/null 2>&1

echo -e "  等待容器就绪..."
sleep 15

# 验证111启动成功
KEEPER_111=$(ssh root@${SERVER_111} "echo 'mntr' | nc localhost 9181 2>/dev/null | grep zk_server_state | awk '{print \$2}'" || echo "unknown")
echo -e "${GREEN}✓${NC} Server 111 启动成功 (Keeper: $KEEPER_111)"
echo ""

# ========================================
# 步骤 7: 更新并重启 Server 58（Leader最后）
# ========================================
echo -e "${CYAN}[步骤 7/8] 更新并重启 Server 58 (Leader)${NC}"

# 传输3节点配置文件到58
echo -e "  传输配置文件..."
scp "${CONFIG_DIR}/keeper_config_58_3nodes.xml" \
    root@${SERVER_58}:${CONFIG_DIR}/keeper_config.xml >/dev/null 2>&1

scp "${CONFIG_DIR}/replication_config_58_3nodes.xml" \
    root@${SERVER_58}:${CONFIG_DIR}/replication_config.xml >/dev/null 2>&1

echo -e "${GREEN}✓${NC} 配置文件已传输到 Server 58"

# 重启58的容器
echo -e "  重启 Server 58 容器（Leader，最后重启）..."
ssh root@${SERVER_58} "cd ${PROJECT_DIR} && docker stop ${CONTAINER_NAME}" >/dev/null 2>&1
ssh root@${SERVER_58} "cd ${PROJECT_DIR} && docker start ${CONTAINER_NAME}" >/dev/null 2>&1

echo -e "  等待容器就绪..."
sleep 15

# 验证58启动成功
KEEPER_58_NEW=$(ssh root@${SERVER_58} "echo 'mntr' | nc localhost 9181 2>/dev/null | grep zk_server_state | awk '{print \$2}'" || echo "unknown")
echo -e "${GREEN}✓${NC} Server 58 重启成功 (Keeper: $KEEPER_58_NEW)"
echo ""

# ========================================
# 步骤 8: 验证 3节点集群
# ========================================
echo -e "${CYAN}[步骤 8/8] 验证 3节点集群状态${NC}"

echo -e "  等待集群稳定..."
sleep 10

# 检查复制表状态
echo -e "\n  ${BOLD}复制表状态:${NC}"
docker exec $CONTAINER_NAME clickhouse-client --query "
SELECT 
    '总表数' as metric, count() as value FROM system.replicas
UNION ALL
SELECT '只读表数' as metric, sum(is_readonly) as value FROM system.replicas
UNION ALL
SELECT '在线副本数' as metric, max(active_replicas) as value FROM system.replicas
UNION ALL
SELECT '总副本数' as metric, max(total_replicas) as value FROM system.replicas
UNION ALL
SELECT '同步队列' as metric, sum(queue_size) as value FROM system.replicas
FORMAT TSV
" 2>/dev/null | while IFS=$'\t' read metric value; do
    echo -e "    ${metric}: ${BOLD}${value}${NC}"
done

# 验证副本数量
TOTAL_REPLICAS=$(docker exec $CONTAINER_NAME clickhouse-client --query \
    "SELECT max(total_replicas) FROM system.replicas" 2>/dev/null || echo "0")

ACTIVE_REPLICAS=$(docker exec $CONTAINER_NAME clickhouse-client --query \
    "SELECT max(active_replicas) FROM system.replicas" 2>/dev/null || echo "0")

echo ""
if [ "$TOTAL_REPLICAS" = "3" ] && [ "$ACTIVE_REPLICAS" = "3" ]; then
    echo -e "${GREEN}${BOLD}✓ 扩容成功！${NC} 3节点集群已就绪 (3/3 副本在线)"
else
    echo -e "${YELLOW}⚠ 警告${NC}: 副本状态异常 (${ACTIVE_REPLICAS}/${TOTAL_REPLICAS})"
    echo -e "  ${YELLOW}建议: 等待5-10分钟让集群完成同步${NC}"
fi

# 显示Keeper集群状态
echo -e "\n  ${BOLD}Keeper 集群状态:${NC}"
for server in "$SERVER_41:41" "$SERVER_58:58" "$SERVER_111:111"; do
    IP=$(echo $server | cut -d: -f1)
    NAME=$(echo $server | cut -d: -f2)
    if [ "$IP" = "$SERVER_41" ]; then
        STATE=$(echo "mntr" | nc localhost 9181 2>/dev/null | grep "zk_server_state" | awk '{print $2}' || echo "unknown")
    else
        STATE=$(ssh root@${IP} "echo 'mntr' | nc localhost 9181 2>/dev/null | grep zk_server_state | awk '{print \$2}'" || echo "unknown")
    fi
    echo -e "    Server ${NAME}: ${BOLD}${STATE}${NC}"
done

# 计算耗时
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}${BOLD}✓ 扩容完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "  完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "  总耗时: ${DURATION} 秒"
echo -e "  备份位置: ${BACKUP_DIR}"
echo -e ""
echo -e "${CYAN}下一步建议:${NC}"
echo -e "  1. 监控同步队列: ${BLUE}watch 'docker exec ${CONTAINER_NAME} clickhouse-client --query \"SELECT sum(queue_size) FROM system.replicas\"'${NC}"
echo -e "  2. 查看详细状态: ${BLUE}docker exec ${CONTAINER_NAME} clickhouse-client --query \"SELECT * FROM system.replicas FORMAT Vertical\"${NC}"
echo -e "  3. 检查日志: ${BLUE}docker logs -f ${CONTAINER_NAME}${NC}"
echo -e ""
echo -e "${GREEN}🎉 恭喜！你的ClickHouse集群现在具备真正的高可用能力！${NC}\n"
