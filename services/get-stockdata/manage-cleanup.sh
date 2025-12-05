#!/bin/bash

# Docker 清理任务管理脚本
# 用于管理和监控 Docker 定时清理任务

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示状态
show_status() {
    echo -e "${BLUE}=== Docker 清理任务状态 ===${NC}"

    # 显示定时器状态
    echo -e "\n${YELLOW}定时器状态:${NC}"
    sudo systemctl status docker-cleanup.timer --no-pager

    # 显示下次执行时间
    echo -e "\n${YELLOW}下次执行时间:${NC}"
    systemctl list-timers docker-cleanup --no-pager

    # 显示最近的清理日志
    echo -e "\n${YELLOW}最近的清理日志:${NC}"
    if [ -f /var/log/docker-cleanup.log ]; then
        sudo tail -10 /var/log/docker-cleanup.log
    else
        echo -e "${RED}系统日志文件不存在${NC}"
        if [ -f ~/docker-cleanup.log ]; then
            echo -e "\n${YELLOW}用户日志:${NC}"
            tail -10 ~/docker-cleanup.log
        fi
    fi

    # 显示 Docker 磁盘使用情况
    echo -e "\n${YELLOW}Docker 磁盘使用情况:${NC}"
    docker system df
}

# 手动执行清理
run_cleanup() {
    echo -e "${BLUE}=== 手动执行 Docker 清理 ===${NC}"
    sudo systemctl start docker-cleanup.service

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 清理任务执行成功${NC}"

        # 显示清理结果
        echo -e "\n${YELLOW}清理结果:${NC}"
        sudo tail -5 /var/log/docker-cleanup.log
    else
        echo -e "${RED}✗ 清理任务执行失败${NC}"
    fi
}

# 启用定时任务
enable_timer() {
    echo -e "${BLUE}=== 启用 Docker 清理定时任务 ===${NC}"
    sudo systemctl enable docker-cleanup.timer
    sudo systemctl start docker-cleanup.timer

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 定时任务已启用${NC}"
        show_status
    else
        echo -e "${RED}✗ 定时任务启用失败${NC}"
    fi
}

# 禁用定时任务
disable_timer() {
    echo -e "${BLUE}=== 禁用 Docker 清理定时任务 ===${NC}"
    sudo systemctl stop docker-cleanup.timer
    sudo systemctl disable docker-cleanup.timer

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 定时任务已禁用${NC}"
    else
        echo -e "${RED}✗ 定时任务禁用失败${NC}"
    fi
}

# 显示帮助信息
show_help() {
    echo -e "${BLUE}Docker 清理任务管理脚本${NC}"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  status    - 显示当前状态"
    echo "  run       - 手动执行清理"
    echo "  enable    - 启用定时任务"
    echo "  disable   - 禁用定时任务"
    echo "  help      - 显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 status     # 查看状态"
    echo "  $0 run        # 立即清理"
    echo "  $0 enable     # 启用定时清理"
}

# 主逻辑
case "$1" in
    status)
        show_status
        ;;
    run)
        run_cleanup
        ;;
    enable)
        enable_timer
        ;;
    disable)
        disable_timer
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}未知命令: $1${NC}"
        show_help
        exit 1
        ;;
esac