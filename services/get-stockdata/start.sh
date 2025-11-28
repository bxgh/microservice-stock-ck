#!/bin/bash

# Get Stock Data 微服务启动脚本
# 自动检测并使用开发环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_header() {
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_fire() {
    echo -e "${PURPLE}🔥 $1${NC}"
}

# 检查 Docker 是否运行
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker 未运行，请先启动 Docker"
        exit 1
    fi
}

# 检查是否在正确的目录
check_directory() {
    if [ ! -f "docker-compose.dev.yml" ]; then
        print_error "请在 services/get-stockdata 目录下运行此脚本"
        exit 1
    fi
}

# 显示菜单
show_menu() {
    print_header "Get Stock Data 微服务启动向导"
    echo ""
    echo "请选择启动模式:"
    echo ""
    echo "  ${GREEN}1)${NC} 🔥 开发环境（推荐）- 支持热加载，修改代码自动生效"
    echo "  ${BLUE}2)${NC} 🚀 生产环境 - 高性能，无热加载"
    echo "  ${YELLOW}3)${NC} 📊 查看服务状态"
    echo "  ${RED}4)${NC} 🛑 停止所有服务"
    echo "  ${CYAN}5)${NC} 📋 查看日志"
    echo "  ${PURPLE}6)${NC} ❓ 帮助文档"
    echo "  ${RED}0)${NC} 退出"
    echo ""
}

# 启动开发环境
start_dev() {
    print_fire "启动开发环境（热加载模式）"
    echo ""
    print_info "特性说明:"
    echo "  • 修改 src/ 目录下的代码会自动重启（1-2秒）"
    echo "  • DEBUG 级别日志，详细输出"
    echo "  • 源码实时挂载，无需重新构建"
    echo ""
    
    read -p "是否后台运行？(y/N): " bg_mode
    
    if [[ $bg_mode =~ ^[Yy]$ ]]; then
        print_info "后台启动开发环境..."
        docker compose -f docker-compose.dev.yml up -d
        print_success "开发环境已在后台启动！"
        print_info "查看日志: ./start.sh 然后选择选项 5"
        print_info "访问: http://localhost:8086/docs"
    else
        print_info "前台启动开发环境..."
        print_warning "按 Ctrl+C 停止服务"
        echo ""
        sleep 2
        docker compose -f docker-compose.dev.yml up
    fi
}

# 启动生产环境
start_prod() {
    print_header "启动生产环境"
    print_warning "生产环境不支持热加载，修改代码需要重新构建"
    echo ""
    read -p "确认启动生产环境？(y/N): " confirm
    
    if [[ $confirm =~ ^[Yy]$ ]]; then
        docker compose up -d
        print_success "生产环境已启动！"
        print_info "访问: http://localhost:8086/docs"
    else
        print_info "已取消"
    fi
}

# 查看状态
show_status() {
    print_header "服务状态"
    docker ps --filter "name=get-stockdata" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || print_warning "没有运行中的容器"
    echo ""
    
    # 检查健康状态
    if curl -s http://localhost:8086/api/v1/health > /dev/null 2>&1; then
        print_success "服务健康状态: ✅ 正常"
        echo ""
        curl -s http://localhost:8086/api/v1/health | python3 -m json.tool 2>/dev/null || true
    else
        print_warning "服务健康状态: ❌ 无法访问"
    fi
}

# 停止服务
stop_services() {
    print_header "停止服务"
    echo "请选择要停止的环境:"
    echo "  1) 开发环境"
    echo "  2) 生产环境"
    echo "  3) 全部停止"
    echo ""
    read -p "请选择 (1-3): " choice
    
    case $choice in
        1)
            docker compose -f docker-compose.dev.yml down
            print_success "开发环境已停止"
            ;;
        2)
            docker compose down
            print_success "生产环境已停止"
            ;;
        3)
            docker compose -f docker-compose.dev.yml down
            docker compose down
            print_success "所有环境已停止"
            ;;
        *)
            print_error "无效选择"
            ;;
    esac
}

# 查看日志
show_logs() {
    print_header "查看日志"
    echo "请选择环境:"
    echo "  1) 开发环境"
    echo "  2) 生产环境"
    echo ""
    read -p "请选择 (1-2): " choice
    
    case $choice in
        1)
            print_info "开发环境日志（Ctrl+C 退出）..."
            sleep 1
            docker compose -f docker-compose.dev.yml logs -f
            ;;
        2)
            print_info "生产环境日志（Ctrl+C 退出）..."
            sleep 1
            docker compose logs -f
            ;;
        *)
            print_error "无效选择"
            ;;
    esac
}

# 显示帮助
show_help() {
    print_header "使用帮助"
    echo ""
    echo "📚 文档链接:"
    echo "  • README.md - 项目总览"
    echo "  • docs/guides/HOT_RELOAD_GUIDE.md - 热加载使用指南"
    echo "  • docs/reports/HOT_RELOAD_TEST_REPORT.md - 热加载测试报告"
    echo ""
    echo "🔥 开发环境特性:"
    echo "  • 自动热加载：修改代码后 1-2 秒自动生效"
    echo "  • DEBUG 日志：详细的调试信息"
    echo "  • 快速迭代：无需重启容器"
    echo ""
    echo "🚀 快速命令:"
    echo "  make dev      - 启动开发环境"
    echo "  make logs     - 查看日志"
    echo "  make health   - 检查健康状态"
    echo "  make help     - 查看所有命令"
    echo ""
    echo "📌 API 文档: http://localhost:8086/docs"
    echo ""
    read -p "按 Enter 继续..."
}

# 主函数
main() {
    # 检查环境
    check_docker
    check_directory
    
    while true; do
        clear
        show_menu
        read -p "请选择 (0-6): " choice
        echo ""
        
        case $choice in
            1)
                start_dev
                read -p "按 Enter 继续..."
                ;;
            2)
                start_prod
                read -p "按 Enter 继续..."
                ;;
            3)
                show_status
                read -p "按 Enter 继续..."
                ;;
            4)
                stop_services
                read -p "按 Enter 继续..."
                ;;
            5)
                show_logs
                ;;
            6)
                show_help
                ;;
            0)
                print_info "再见！"
                exit 0
                ;;
            *)
                print_error "无效选择，请重新输入"
                sleep 2
                ;;
        esac
    done
}

# 运行主函数
main
