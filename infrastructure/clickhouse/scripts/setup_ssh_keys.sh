#!/bin/bash

# SSH免密登录配置脚本
# 使用方法: bash setup_ssh_keys.sh

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}配置SSH免密登录${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 检查SSH密钥
if [ ! -f ~/.ssh/id_rsa.pub ]; then
    echo -e "${YELLOW}[1/3] 生成SSH密钥${NC}"
    ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa -q
    echo -e "${GREEN}✓${NC} SSH密钥已生成"
else
    echo -e "${GREEN}✓${NC} SSH密钥已存在"
fi

echo ""
echo -e "${YELLOW}[2/3] 传输公钥到Server 58${NC}"
echo -e "  请输入 ${BLUE}192.168.151.58${NC} 的root密码:"
ssh-copy-id -o StrictHostKeyChecking=no root@192.168.151.58

echo ""
echo -e "${YELLOW}[3/3] 传输公钥到Server 111${NC}"
echo -e "  请输入 ${BLUE}192.168.151.111${NC} 的root密码:"
ssh-copy-id -o StrictHostKeyChecking=no root@192.168.151.111

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ SSH免密登录配置完成！${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 验证
echo -e "${YELLOW}验证SSH连接:${NC}"
echo -n "  Server 58: "
ssh -o BatchMode=yes root@192.168.151.58 "hostname" 2>/dev/null && echo -e "${GREEN}✓ OK${NC}" || echo -e "${RED}✗ 失败${NC}"

echo -n "  Server 111: "
ssh -o BatchMode=yes root@192.168.151.111 "hostname" 2>/dev/null && echo -e "${GREEN}✓ OK${NC}" || echo -e "${RED}✗ 失败${NC}"

echo ""
echo -e "${GREEN}现在可以执行扩容脚本了！${NC}"
echo -e "${BLUE}sudo bash infrastructure/clickhouse/scripts/one_click_expansion.sh${NC}\n"
