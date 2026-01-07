#!/bin/bash

# ClickHouse 3节点扩容前置检查脚本
# 用途: 在执行扩容前验证所有前置条件
# 使用方法: 
#   - 在111服务器上运行: bash pre_expansion_check.sh 111
#   - 在41服务器上运行: bash pre_expansion_check.sh 41
#   - 在58服务器上运行: bash pre_expansion_check.sh 58

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 当前服务器ID
CURRENT_SERVER=${1:-"unknown"}

# 服务器IP定义
SERVER_41="192.168.151.41"
SERVER_58="192.168.151.58"
SERVER_111="192.168.151.111"

# 检查计数器
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ClickHouse 3节点扩容前置检查${NC}"
echo -e "${BLUE}当前服务器: ${CURRENT_SERVER}${NC}"
echo -e "${BLUE}检查时间: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 辅助函数
check_pass() {
    echo -e "${GREEN}✓ PASS${NC} - $1"
    ((PASS_COUNT++))
}

check_fail() {
    echo -e "${RED}✗ FAIL${NC} - $1"
    ((FAIL_COUNT++))
}

check_warn() {
    echo -e "${YELLOW}⚠ WARN${NC} - $1"
    ((WARN_COUNT++))
}

# ========================================
# 1. 系统基础检查
# ========================================
echo -e "\n${BLUE}[1/7] 系统基础检查${NC}"

# 检查是否为root或有sudo权限
if [ "$EUID" -ne 0 ] && ! sudo -n true 2>/dev/null; then
    check_fail "需要 root 权限或 sudo 权限"
else
    check_pass "权限检查通过"
fi

# 检查操作系统
OS_INFO=$(cat /etc/os-release | grep "^PRETTY_NAME" | cut -d'"' -f2)
echo -e "  操作系统: ${OS_INFO}"

# 检查磁盘空间
DISK_USAGE=$(df -h /var/lib/clickhouse 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//')
if [ -z "$DISK_USAGE" ]; then
    check_warn "无法检查 ClickHouse 数据目录磁盘空间"
elif [ "$DISK_USAGE" -gt 80 ]; then
    check_fail "磁盘空间不足 (使用率: ${DISK_USAGE}%)"
else
    check_pass "磁盘空间充足 (使用率: ${DISK_USAGE}%)"
fi

# ========================================
# 2. ClickHouse 服务检查
# ========================================
echo -e "\n${BLUE}[2/7] ClickHouse 服务检查${NC}"

# 检查 ClickHouse 是否安装
if command -v clickhouse-server &> /dev/null; then
    CH_VERSION=$(clickhouse-server --version 2>/dev/null | head -1 || echo "unknown")
    check_pass "ClickHouse 已安装"
    echo -e "  版本: ${CH_VERSION}"
else
    check_fail "ClickHouse 未安装"
fi

# 检查 ClickHouse 服务状态
if systemctl is-active --quiet clickhouse-server; then
    check_pass "ClickHouse 服务运行中"
    
    # 检查是否可以连接
    if clickhouse-client --query "SELECT 1" &> /dev/null; then
        check_pass "ClickHouse 客户端连接成功"
    else
        check_fail "ClickHouse 客户端连接失败"
    fi
else
    if [ "$CURRENT_SERVER" == "111" ]; then
        check_warn "ClickHouse 服务未运行 (新节点首次配置时正常)"
    else
        check_fail "ClickHouse 服务未运行"
    fi
fi

# ========================================
# 3. 网络连通性检查
# ========================================
echo -e "\n${BLUE}[3/7] 网络连通性检查${NC}"

check_port() {
    local host=$1
    local port=$2
    local desc=$3
    
    if timeout 2 bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null; then
        check_pass "${desc} - ${host}:${port} 连通"
    else
        check_fail "${desc} - ${host}:${port} 不通"
    fi
}

# 检查到所有节点的连通性
for server in $SERVER_41 $SERVER_58 $SERVER_111; do
    echo -e "\n  检查到 ${server} 的连通性:"
    check_port $server 9000 "ClickHouse 原生协议 (9000)"
    check_port $server 9009 "副本同步端口 (9009)"
    check_port $server 9181 "Keeper 客户端 (9181)"
    check_port $server 9234 "Keeper Raft (9234)"
done

# ========================================
# 4. 配置文件检查
# ========================================
echo -e "\n${BLUE}[4/7] 配置文件检查${NC}"

CONFIG_DIR="/etc/clickhouse-server/config.d"

if [ -d "$CONFIG_DIR" ]; then
    check_pass "配置目录存在: $CONFIG_DIR"
    
    # 检查关键配置文件
    if [ -f "$CONFIG_DIR/keeper_config.xml" ]; then
        check_pass "Keeper 配置文件存在"
        
        # 检查 server_id
        server_id=$(grep -oP '<server_id>\K[0-9]+' "$CONFIG_DIR/keeper_config.xml" 2>/dev/null || echo "")
        if [ -n "$server_id" ]; then
            echo -e "  当前 Keeper server_id: ${server_id}"
            if [ "$CURRENT_SERVER" == "41" ] && [ "$server_id" != "1" ]; then
                check_warn "server_id 不匹配 (期望: 1, 实际: $server_id)"
            elif [ "$CURRENT_SERVER" == "58" ] && [ "$server_id" != "2" ]; then
                check_warn "server_id 不匹配 (期望: 2, 实际: $server_id)"
            elif [ "$CURRENT_SERVER" == "111" ] && [ "$server_id" != "3" ]; then
                check_warn "server_id 不匹配 (期望: 3, 实际: $server_id)"
            fi
        fi
    else
        check_warn "Keeper 配置文件不存在 (如果是新节点，需要先部署配置)"
    fi
    
    if [ -f "$CONFIG_DIR/replication_config.xml" ]; then
        check_pass "复制配置文件存在"
        
        # 检查 replica 名称
        replica=$(grep -oP '<replica>\K[^<]+' "$CONFIG_DIR/replication_config.xml" 2>/dev/null | head -1 || echo "")
        if [ -n "$replica" ]; then
            echo -e "  当前 Replica 名称: ${replica}"
        fi
    else
        check_warn "复制配置文件不存在 (如果是新节点，需要先部署配置)"
    fi
else
    check_fail "配置目录不存在: $CONFIG_DIR"
fi

# ========================================
# 5. Keeper 集群状态检查 (仅对现有节点)
# ========================================
echo -e "\n${BLUE}[5/7] Keeper 集群状态检查${NC}"

if [ "$CURRENT_SERVER" != "111" ] && systemctl is-active --quiet clickhouse-server; then
    # 检查 Keeper 状态
    KEEPER_STATUS=$(echo "mntr" | nc localhost 9181 2>/dev/null | grep "zk_server_state" | awk '{print $2}' || echo "unknown")
    
    if [ "$KEEPER_STATUS" == "leader" ] || [ "$KEEPER_STATUS" == "follower" ]; then
        check_pass "Keeper 状态正常: $KEEPER_STATUS"
    else
        check_fail "Keeper 状态异常: $KEEPER_STATUS"
    fi
    
    # 检查 Keeper 版本
    ZK_VERSION=$(echo "mntr" | nc localhost 9181 2>/dev/null | grep "zk_version" | awk '{print $2}' || echo "unknown")
    echo -e "  Keeper 版本: ${ZK_VERSION}"
    
else
    check_warn "跳过 Keeper 状态检查 (新节点或服务未运行)"
fi

# ========================================
# 6. 复制表状态检查 (仅对现有节点)
# ========================================
echo -e "\n${BLUE}[6/7] 复制表状态检查${NC}"

if [ "$CURRENT_SERVER" != "111" ] && clickhouse-client --query "SELECT 1" &> /dev/null; then
    # 查询复制表数量
    REPLICA_COUNT=$(clickhouse-client --query "SELECT count() FROM system.replicas" 2>/dev/null || echo "0")
    echo -e "  复制表数量: ${REPLICA_COUNT}"
    
    # 检查是否有只读表
    READONLY_COUNT=$(clickhouse-client --query "SELECT count() FROM system.replicas WHERE is_readonly = 1" 2>/dev/null || echo "0")
    if [ "$READONLY_COUNT" -eq 0 ]; then
        check_pass "无只读复制表"
    else
        check_fail "存在 ${READONLY_COUNT} 个只读复制表"
    fi
    
    # 检查是否有同步队列积压
    QUEUE_SIZE=$(clickhouse-client --query "SELECT sum(queue_size) FROM system.replicas" 2>/dev/null || echo "0")
    if [ "$QUEUE_SIZE" -lt 100 ]; then
        check_pass "同步队列正常 (积压: ${QUEUE_SIZE})"
    else
        check_warn "同步队列有积压 (积压: ${QUEUE_SIZE})"
    fi
    
    # 检查副本数量
    TOTAL_REPLICAS=$(clickhouse-client --query "SELECT total_replicas FROM system.replicas LIMIT 1" 2>/dev/null || echo "0")
    ACTIVE_REPLICAS=$(clickhouse-client --query "SELECT active_replicas FROM system.replicas LIMIT 1" 2>/dev/null || echo "0")
    
    if [ "$TOTAL_REPLICAS" -eq "$ACTIVE_REPLICAS" ]; then
        check_pass "所有副本在线 (${ACTIVE_REPLICAS}/${TOTAL_REPLICAS})"
    else
        check_fail "副本未全部在线 (${ACTIVE_REPLICAS}/${TOTAL_REPLICAS})"
    fi
else
    check_warn "跳过复制表检查 (新节点或连接失败)"
fi

# ========================================
# 7. 备份检查
# ========================================
echo -e "\n${BLUE}[7/7] 备份检查${NC}"

BACKUP_DIR="/backup"
if [ -d "$BACKUP_DIR" ]; then
    check_pass "备份目录存在: $BACKUP_DIR"
    
    # 检查今天是否有备份
    TODAY=$(date +%Y%m%d)
    if ls "$BACKUP_DIR"/*${TODAY}* 1> /dev/null 2>&1; then
        check_pass "今日已有备份"
        ls -lh "$BACKUP_DIR"/*${TODAY}* | awk '{print "  - " $9 " (" $5 ")"}'
    else
        check_warn "今日尚未备份 (强烈建议在扩容前备份)"
    fi
else
    check_warn "备份目录不存在: $BACKUP_DIR (建议创建并备份)"
fi

# ========================================
# 总结
# ========================================
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}检查结果汇总${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ 通过: ${PASS_COUNT}${NC}"
echo -e "${YELLOW}⚠ 警告: ${WARN_COUNT}${NC}"
echo -e "${RED}✗ 失败: ${FAIL_COUNT}${NC}"

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "\n${GREEN}✓ 所有关键检查通过，可以进行扩容！${NC}"
    exit 0
else
    echo -e "\n${RED}✗ 存在 ${FAIL_COUNT} 个失败项，请先修复后再进行扩容${NC}"
    exit 1
fi
