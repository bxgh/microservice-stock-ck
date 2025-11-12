#!/bin/bash

# Task Scheduler 微服务部署脚本
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."

    # 检查Python3
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi

    # 检查aiohttp
    if ! python3 -c "import aiohttp" &> /dev/null; then
        log_warn "aiohttp 未安装，正在安装..."
        sudo apt update && sudo apt install -y python3-aiohttp python3-requests
    fi

    # 检查jq
    if ! command -v jq &> /dev/null; then
        log_warn "jq 未安装，正在安装..."
        sudo apt install -y jq
    fi

    log_success "依赖检查完成"
}

# 检查基础设施
check_infrastructure() {
    log_info "检查基础设施服务..."

    # 检查Nacos
    if curl -s -f "http://localhost:8848/nacos/" &> /dev/null; then
        log_success "✅ Nacos 服务正常"
    else
        log_error "❌ Nacos 服务不可用"
        exit 1
    fi

    # 检查Redis
    if timeout 3 bash -c "</dev/tcp/localhost/6379" &> /dev/null; then
        log_success "✅ Redis 服务正常"
    else
        log_error "❌ Redis 服务不可用"
        exit 1
    fi

    # 检查ClickHouse
    if curl -s -f "http://localhost:8123/ping" &> /dev/null; then
        log_success "✅ ClickHouse 服务正常"
    else
        log_error "❌ ClickHouse 服务不可用"
        exit 1
    fi

    log_success "基础设施检查完成"
}

# 部署服务 - 只支持Docker Compose
deploy_service() {
    log_info "部署 Task Scheduler 微服务 (Docker Compose)..."
    deploy_compose
}

# Docker Compose部署
deploy_compose() {
    log_info "使用Docker Compose部署..."

    # 检查docker-compose.yml文件
    if [ ! -f "docker-compose.yml" ]; then
        log_error "docker-compose.yml 文件不存在"
        exit 1
    fi

    # 构建FastAPI镜像（使用Dockerfile）
    log_info "构建FastAPI Task Scheduler镜像..."

    # 检查requirements.txt文件
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt 文件不存在"
        exit 1
    fi

    # 检查src目录
    if [ ! -d "src" ]; then
        log_error "src 目录不存在"
        exit 1
    fi

    # 使用docker build构建镜像
    docker build \
        --build-arg http_proxy=http://192.168.151.18:3128 \
        --build-arg https_proxy=http://192.168.151.18:3128 \
        -t task-scheduler:latest .

    if [ $? -ne 0 ]; then
        log_error "FastAPI镜像构建失败"
        exit 1
    fi

    log_success "✅ FastAPI Task Scheduler镜像构建成功"

    # 使用docker-compose部署
    log_info "使用docker-compose启动服务..."
    docker-compose down 2>/dev/null || true
    docker-compose up -d

    # 等待服务启动
    sleep 10

    # 检查服务状态
    if curl -s -f "http://localhost:8081/health" &> /dev/null; then
        log_success "✅ Task Scheduler Docker Compose部署成功"
    else
        log_error "❌ Task Scheduler Docker Compose部署失败"
        docker-compose logs task-scheduler
        exit 1
    fi
}


# 验证部署
verify_deployment() {
    log_info "验证部署..."

    # 等待服务启动
    sleep 5

    # 检查健康状态
    if curl -s -f "http://localhost:8081/health" &> /dev/null; then
        log_success "✅ 健康检查通过"
    else
        log_error "❌ 健康检查失败"
        exit 1
    fi

    # 检查Nacos注册
    if curl -s "http://localhost:8848/nacos/v1/ns/instance/list?serviceName=task-scheduler" | grep -q "healthy.*true"; then
        log_success "✅ Nacos服务注册成功"
    else
        log_warn "⚠️ Nacos服务注册可能需要更多时间"
    fi

    log_success "🎉 部署验证成功！"
}

# 停止服务
stop_service() {
    log_info "停止 Task Scheduler 微服务..."
    docker-compose down 2>/dev/null || true
    docker stop task-scheduler 2>/dev/null || true
    docker rm task-scheduler 2>/dev/null || true
    log_success "服务已停止"
}

# 查看日志
show_logs() {
    if docker ps -q -f name=task-scheduler > /dev/null 2>&1; then
        docker logs -f task-scheduler
    elif [ -f "app.log" ]; then
        tail -f app.log
    else
        log_error "Task Scheduler 服务未运行，无日志可查看"
        exit 1
    fi
}

# 显示帮助
show_help() {
    echo "用法: $0 {deploy|stop|restart|logs|status|verify|help}"
    echo ""
    echo "命令:"
    echo "  deploy          - 部署Task Scheduler服务 (Docker Compose)"
    echo "  stop            - 停止Task Scheduler服务"
    echo "  restart         - 重启Task Scheduler服务"
    echo "  logs            - 查看Task Scheduler日志"
    echo "  status          - 查看Task Scheduler状态"
    echo "  verify          - 验证Task Scheduler部署"
    echo "  help            - 显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 deploy          # 部署Task Scheduler"
    echo "  $0 restart          # 重启Task Scheduler"
    echo "  $0 logs             # 查看日志"
}

# 查看状态
show_status() {
    log_info "Task Scheduler 服务状态:"

    if docker ps -q -f name=task-scheduler > /dev/null 2>&1; then
        echo "容器状态: 运行中"
        echo "容器ID: $(docker ps -q -f name=task-scheduler)"

        # 资源使用情况
        echo "资源使用:"
        docker stats --no-stream task-scheduler | tail -n +2

        # 健康检查
        if curl -s -f "http://localhost:8081/health" > /dev/null; then
            echo "健康检查: 通过"
        else
            echo "健康检查: 失败"
        fi

        # 端口信息
        echo "端口映射: $(docker port task-scheduler 8081 | head -n 1)"
    else
        echo "容器状态: 未运行"
    fi
}

# 主函数
main() {
    echo "========================================"
    echo "     Task Scheduler 微服务部署脚本"
    echo "========================================"
    echo ""

    case "${1:-deploy}" in
        deploy)
            check_dependencies
            check_infrastructure
            deploy_service
            verify_deployment
            ;;
        stop)
            stop_service
            ;;
        restart)
            stop_service
            sleep 2
            check_dependencies
            check_infrastructure
            deploy_service
            verify_deployment
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        verify)
            verify_deployment
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"