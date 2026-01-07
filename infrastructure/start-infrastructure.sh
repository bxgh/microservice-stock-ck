#!/bin/bash

# 微服务基础设施启动脚本
# 用于启动和管理所有基础设施服务

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

# 创建必要的目录
create_directories() {
    log_info "创建基础设施数据目录..."

    directories=(
        "./data/nacos/data"
        "./data/nacos/logs"
        "./data/redis"
        "./data/clickhouse/data"
        "./data/clickhouse/logs"
        "./data/rabbitmq"
        "./data/prometheus"
        "./data/grafana"
        "./data/nginx/logs"
        "./data/gitlab/config"
        "./data/gitlab/logs"
        "./data/gitlab/data"
        "./logs"
    )

    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        log_info "创建目录: $dir"
    done
}

# 启动核心服务（必需）
start_core_services() {
    log_info "启动核心服务..."

    services=("nacos" "redis" "clickhouse")

    for service in "${services[@]}"; do
        log_info "启动 $service 服务..."
        if docker compose -f docker-compose.infrastructure.yml up -d "$service"; then
            log_success "$service 启动成功"
        else
            log_error "$service 启动失败"
            return 1
        fi
        sleep 5
    done
}

# 启动监控服务
start_monitoring_services() {
    log_info "启动监控服务..."

    services=("prometheus" "grafana")

    for service in "${services[@]}"; do
        log_info "启动 $service 服务..."
        if docker compose -f docker-compose.infrastructure.yml up -d "$service"; then
            log_success "$service 启动成功"
        else
            log_error "$service 启动失败"
            return 1
        fi
        sleep 3
    done
}

# 启动消息队列
start_message_services() {
    log_info "启动消息队列服务..."

    if docker compose -f docker-compose.infrastructure.yml up -d "rabbitmq"; then
        log_success "RabbitMQ 启动成功"
    else
        log_error "RabbitMQ 启动失败"
        return 1
    fi
    sleep 5
}

# 启动网关服务
start_gateway_services() {
    log_info "启动API网关服务..."

    if docker compose -f docker-compose.infrastructure.yml up -d "nginx"; then
        log_success "Nginx 网关启动成功"
    else
        log_error "Nginx 网关启动失败"
        return 1
    fi
}

# 启动GitLab服务
start_gitlab_service() {
    log_info "启动 GitLab 服务..."

    if [ ! -f "./gitlab/docker-compose.yml" ]; then
        log_error "GitLab 配置文件不存在"
        return 1
    fi

    if cd ./gitlab && docker compose up -d; then
        log_success "GitLab 启动成功"
        cd ..
    else
        log_error "GitLab 启动失败"
        cd ..
        return 1
    fi
}

# 等待服务启动
wait_for_services() {
    local services=("$@")

    log_info "等待服务启动完成..."

    for service_name in "${services[@]}"; do
        local container_name="microservice-stock-$service_name"
        local max_attempts=30
        local attempt=0

        log_info "等待 $service_name 服务就绪..."

        while [ $attempt -lt $max_attempts ]; do
            if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container_name.*Up.*healthy\|$container_name.*Up"; then
                log_success "$service_name 服务已就绪"
                break
            fi

            # 尝试健康检查
            case $service_name in
                "nacos")
                    if curl -s -f "http://localhost:8848/nacos/" &> /dev/null; then
                        log_success "$service_name 服务已就绪"
                        break
                    fi
                    ;;
                "redis")
                    if docker exec $container_name redis-cli ping &> /dev/null; then
                        log_success "$service_name 服务已就绪"
                        break
                    fi
                    ;;
                "clickhouse")
                    if curl -s -f "http://localhost:8123/ping" &> /dev/null; then
                        log_success "$service_name 服务已就绪"
                        break
                    fi
                    ;;
            esac

            attempt=$((attempt + 1))
            sleep 3
            echo -n "."
        done

        if [ $attempt -eq $max_attempts ]; then
            log_warn "$service_name 服务启动超时"
            return 1
        fi
    done
}

# 显示服务信息
show_services_info() {
    log_info "🚀 基础设施服务启动完成！"
    echo "========================================"
    echo "📊 服务访问地址:"
    echo ""
    echo "🏢 服务注册发现 (Nacos):"
    echo "   控制台: http://localhost:8848/nacos"
    echo "   API: http://localhost:8848/nacos/v1"
    echo "   用户名: nacos"
    echo "   密码: nacos"
    echo ""
    echo "🗄️ 缓存服务 (Redis):"
    echo "   端口: localhost:6379"
    echo "   密码: redis123"
    echo ""
    echo "📊 时序数据库 (ClickHouse):"
    echo "   HTTP接口: http://localhost:8123"
    echo "   TCP接口: localhost:9000"
    echo "   管理界面: http://localhost:8123/play"
    echo ""
    echo "📬 消息队列 (RabbitMQ):"
    echo "   管理界面: http://localhost:15672"
    echo "   用户名: admin"
    echo "   密码: admin123"
    echo "   AMQP端口: localhost:5672"
    echo ""
    echo "📈 监控服务 (Prometheus):"
    echo "   Web界面: http://localhost:9090"
    echo "   配置: http://localhost:9090/targets"
    echo ""
    echo "📊 监控界面 (Grafana):"
    echo "   Web界面: http://localhost:3000"
    echo "   用户名: admin"
    echo "   密码: admin123"
    echo ""
    echo "🌐 API网关 (Nginx):"
    echo "   HTTP: http://localhost:80"
    echo "   HTTPS: http://localhost:443"
    echo "========================================"
}

# 检查服务状态
check_services_status() {
    log_info "检查服务运行状态..."

    services=("nacos" "redis" "clickhouse" "rabbitmq" "prometheus" "grafana" "nginx" "gitlab")

    echo "服务状态:"
    echo "----------"

    for service in "${services[@]}"; do
        local container_name="microservice-stock-$service"
        local status=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep "$container_name" 2>/dev/null || echo "未运行")

        if [ -n "$status" ]; then
            echo "  ✅ $service: $status"
        else
            echo "  ❌ $service: 未运行"
        fi
    done
}

# 停止所有服务
stop_services() {
    log_info "停止所有基础设施服务..."

    if docker compose -f docker-compose.infrastructure.yml ps -q | grep -q "."; then
        docker compose -f docker-compose.infrastructure.yml down
        log_success "所有服务已停止"
    else
        log_info "没有运行中的服务"
    fi
}

# 查看日志
show_logs() {
    local service="$1"

    if [ -z "$service" ]; then
        log_info "显示所有服务日志..."
        docker compose -f docker-compose.infrastructure.yml logs -f
    else
        local container_name="microservice-stock-$service"
        log_info "显示 $service 服务日志..."
        docker logs -f "$container_name" 2>/dev/null || {
            log_error "容器 $container_name 不存在"
            docker compose -f docker-compose.infrastructure.yml logs "$service" -f
        }
    fi
}

# 重启服务
restart_service() {
    local service="$1"

    if [ -z "$service" ]; then
        log_info "重启所有基础设施服务..."
        docker compose -f docker-compose.infrastructure.yml down
        sleep 5
        start_core_services
        start_monitoring_services
        start_message_services
        start_gateway_services
        wait_for_services nacos redis clickhouse
        show_services_info
    else
        log_info "重启 $service 服务..."
        docker compose -f docker-compose.infrastructure.yml restart "$service"
        wait_for_services "$service"
        log_success "$service 服务重启完成"
    fi
}

# 清理数据
clean_data() {
    log_warn "⚠️  这将删除所有基础设施数据！"
    read -p "确定要继续吗？(y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "已取消清理操作"
        return 0
    fi

    log_info "清理基础设施数据..."

    # 停止服务
    docker compose -f docker-compose.infrastructure.yml down

    # 删除数据卷
    volumes=("nacos_data" "nacos_logs" "redis_data" "clickhouse_data" "clickhouse_logs"
              "rabbitmq_data" "rabbitmq_logs" "prometheus_data" "grafana_data" "nginx_logs")

    for volume in "${volumes[@]}"; do
        if docker volume ls | grep -q "$volume"; then
            docker volume rm "$volume"
            log_info "删除数据卷: $volume"
        fi
    done

    log_success "所有数据已清理"
}

# 主函数
main() {
    echo "========================================"
    echo "     微服务基础设施管理脚本"
    echo "========================================"
    echo ""

    check_docker
    create_directories

    case "${1:-start}" in
        start)
            log_info "启动基础设施服务..."
            start_core_services
            start_monitoring_services
            start_message_services
            start_gateway_services
            start_gitlab_service
            wait_for_services nacos redis clickhouse
            show_services_info
            ;;
        start-core)
            log_info "启动核心服务（Nacos, Redis, ClickHouse）..."
            start_core_services
            wait_for_services nacos redis clickhouse
            ;;
        start-monitoring)
            log_info "启动监控服务（Prometheus, Grafana）..."
            start_monitoring_services
            ;;
        start-message)
            log_info "启动消息队列服务（RabbitMQ）..."
            start_message_services
            ;;
        start-gateway)
            log_info "启动API网关服务（Nginx）..."
            start_gateway_services
            ;;
        stop)
            log_info "停止所有服务..."
            stop_services
            ;;
        status)
            log_info "检查服务状态..."
            check_services_status
            ;;
        restart)
            log_info "重启服务..."
            restart_service "$2"
            ;;
        logs)
            log_info "查看服务日志..."
            show_logs "$2"
            ;;
        clean)
            clean_data
            ;;
        *)
            echo "用法: $0 {start|start-core|start-monitoring|start-message|start-gateway|stop|status|restart|logs|clean} [service_name]"
            echo ""
            echo "命令说明:"
            echo "  start          - 启动所有基础设施服务"
            echo "  start-core      - 只启动核心服务（Nacos, Redis, ClickHouse）"
            echo "  start-monitoring - 启动监控服务（Prometheus, Grafana）"
            echo "  start-message   - 启动消息队列（RabbitMQ）"
            echo "  start-gateway  - 启动API网关（Nginx）"
            echo "  stop           - 停止所有服务"
            echo "  status        - 检查服务状态"
            echo "  restart        - 重启指定服务或所有服务"
            echo "  logs          - 查看服务日志"
            echo "  clean         - 清理所有数据"
            echo ""
            echo "示例:"
            echo "  $0 start                    # 启动所有服务"
            echo "  $0 stop                     # 停止所有服务"
            echo "  $0 restart                  # 重启所有服务"
            echo "  $0 restart nacos            # 重启Nacos服务"
            echo "  $0 logs nacos              # 查看Nacos日志"
            exit 1
            ;;
    esac
}

# 处理命令行参数
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi