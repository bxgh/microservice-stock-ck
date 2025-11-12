#!/bin/bash

# Nacos 启动脚本
# 用于启动和初始化 Nacos 服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
}

# 检查配置文件
check_config() {
    log_info "检查 Nacos 配置文件..."

    config_dir="./infrastructure/nacos/config"
    required_files=(
        "application.properties"
        "nacos-logback.xml"
        "cluster.conf"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$config_dir/$file" ]; then
            log_error "配置文件 $file 不存在: $config_dir/$file"
            exit 1
        fi
    done

    log_info "所有配置文件检查通过"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的数据目录..."

    directories=(
        "./data/nacos/data"
        "./data/nacos/logs"
        "./logs/nacos"
    )

    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        log_info "创建目录: $dir"
    done
}

# 启动 Nacos
start_nacos() {
    log_info "启动 Nacos 服务..."

    # 检查是否已经运行
    if docker ps --format "table {{.Names}}" | grep -q "microservice-stock-nacos"; then
        log_warn "Nacos 容器已在运行"
        return 0
    fi

    # 启动 Nacos
    if [ -f "docker-compose.nacos.yml" ]; then
        docker compose -f docker-compose.nacos.yml up -d nacos
    elif [ -f "docker-compose.infrastructure.yml" ]; then
        docker compose -f docker-compose.infrastructure.yml up -d nacos
    else
        log_error "未找到 Docker Compose 文件"
        exit 1
    fi

    log_info "Nacos 启动命令已执行"
}

# 等待 Nacos 启动
wait_for_nacos() {
    log_info "等待 Nacos 启动..."

    local max_attempts=60
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f http://localhost:8848/nacos/v1/console/health &> /dev/null; then
            log_info "Nacos 启动成功！"
            return 0
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    log_error "Nacos 启动超时"
    return 1
}

# 显示 Nacos 信息
show_nacos_info() {
    log_info "Nacos 服务信息:"
    echo "========================"
    echo "访问地址: http://localhost:8848/nacos"
    echo "默认用户名: nacos"
    echo "默认密码: nacos"
    echo "健康检查: http://localhost:8848/nacos/v1/console/health"
    echo "API文档: http://localhost:8848/nacos/v1/console/api"
    echo "========================"
}

# 检查 Nacos 状态
check_nacos_status() {
    log_info "检查 Nacos 运行状态..."

    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "microservice-stock-nacos"; then
        local status=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep "microservice-stock-nacos" | awk '{print $2,$3,$4}')
        log_info "Nacos 容器状态: $status"

        if curl -s -f http://localhost:8848/nacos/v1/console/health &> /dev/null; then
            log_info "Nacos 服务健康状态: 正常"
            return 0
        else
            log_warn "Nacos 服务健康状态: 异常"
            return 1
        fi
    else
        log_error "Nacos 容器未运行"
        return 1
    fi
}

# 主函数
main() {
    echo "========================================"
    echo "      Nacos 启动脚本"
    echo "========================================"

    check_docker
    check_config
    create_directories
    start_nacos

    if wait_for_nacos; then
        show_nacos_info
        check_nacos_status
        log_info "Nacos 启动完成！"
    else
        log_error "Nacos 启动失败，请检查日志"
        docker logs microservice-stock-nacos
        exit 1
    fi
}

# 停止 Nacos
stop_nacos() {
    log_info "停止 Nacos 服务..."

    if docker ps --format "table {{.Names}}" | grep -q "microservice-stock-nacos"; then
        docker stop microservice-stock-nacos
        docker rm microservice-stock-nacos
        log_info "Nacos 已停止并删除容器"
    else
        log_warn "Nacos 容器未运行"
    fi
}

# 重启 Nacos
restart_nacos() {
    log_info "重启 Nacos 服务..."
    stop_nacos
    sleep 2
    main
}

# 查看日志
show_logs() {
    log_info "显示 Nacos 日志..."
    docker logs -f microservice-stock-nacos
}

# 处理命令行参数
case "${1:-start}" in
    start)
        main
        ;;
    stop)
        stop_nacos
        ;;
    restart)
        restart_nacos
        ;;
    status)
        check_nacos_status
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs}"
        echo "  start   - 启动 Nacos (默认)"
        echo "  stop    - 停止 Nacos"
        echo "  restart - 重启 Nacos"
        echo "  status  - 检查 Nacos 状态"
        echo "  logs    - 查看 Nacos 日志"
        exit 1
        ;;
esac