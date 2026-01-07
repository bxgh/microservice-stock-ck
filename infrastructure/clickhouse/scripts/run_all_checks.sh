#!/bin/bash

# ClickHouse 3节点扩容 - 一键前置检查
# 用途: 自动传输脚本到所有服务器并执行前置检查
# 使用方法: bash run_all_checks.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 服务器列表
SERVERS=("41" "58" "111")
SERVER_IPS=("192.168.151.41" "192.168.151.58" "192.168.151.111")

# 脚本路径
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/pre_expansion_check.sh"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ClickHouse 3节点扩容 - 批量前置检查${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 检查脚本是否存在
if [ ! -f "$SCRIPT_PATH" ]; then
    echo -e "${RED}错误: 找不到检查脚本 $SCRIPT_PATH${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} 检查脚本已找到: $SCRIPT_PATH\n"

# 检查SSH连接
echo -e "${BLUE}[1/3] 检查SSH连接${NC}"
for i in "${!SERVERS[@]}"; do
    server="${SERVERS[$i]}"
    ip="${SERVER_IPS[$i]}"
    
    echo -n "  检查 Server $server ($ip)... "
    if ssh -o ConnectTimeout=5 -o BatchMode=yes root@$ip "exit" 2>/dev/null; then
        echo -e "${GREEN}✓ 连通${NC}"
    else
        echo -e "${YELLOW}⚠ SSH连接失败，请确保已配置SSH密钥${NC}"
        echo -e "${YELLOW}  提示: ssh-copy-id root@$ip${NC}"
    fi
done

echo ""

# 传输脚本
echo -e "${BLUE}[2/3] 传输检查脚本${NC}"
for i in "${!SERVERS[@]}"; do
    server="${SERVERS[$i]}"
    ip="${SERVER_IPS[$i]}"
    
    echo -n "  传输到 Server $server ($ip)... "
    if scp -o ConnectTimeout=5 "$SCRIPT_PATH" root@$ip:/tmp/pre_expansion_check.sh 2>/dev/null; then
        echo -e "${GREEN}✓ 成功${NC}"
    else
        echo -e "${RED}✗ 失败${NC}"
    fi
done

echo ""

# 执行检查
echo -e "${BLUE}[3/3] 执行前置检查${NC}\n"
for i in "${!SERVERS[@]}"; do
    server="${SERVERS[$i]}"
    ip="${SERVER_IPS[$i]}"
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Server $server ($ip) 检查结果${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    ssh root@$ip "bash /tmp/pre_expansion_check.sh $server" || echo -e "${RED}检查失败${NC}"
    
    echo ""
done

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}批量检查完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "\n${YELLOW}请查看上方输出，确认所有服务器的检查结果${NC}\n"
