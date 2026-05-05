#!/bin/bash

# Backend Smart Commit - 后端智能提交脚本
# 这个脚本是 git-back-commit 斜杠命令的实际执行器

set -e

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/git-smart-commit.py"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查Python环境
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装或不在PATH中"
        exit 1
    fi

    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    log_info "使用 Python 版本: $python_version"
}

# 检查Git仓库
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "当前目录不是Git仓库"
        exit 1
    fi

    log_info "Git仓库: $(git remote get-url origin 2>/dev/null || echo '本地仓库')"
}

# 检查Python脚本
check_python_script() {
    if [[ ! -f "$PYTHON_SCRIPT" ]]; then
        log_error "Python脚本不存在: $PYTHON_SCRIPT"
        exit 1
    fi

    # 确保脚本可执行
    chmod +x "$PYTHON_SCRIPT"
    log_info "找到智能提交脚本: $PYTHON_SCRIPT"
}

# 解析命令行参数
parse_args() {
    DRY_RUN=false
    VERBOSE=false
    HELP=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run|-n)
                DRY_RUN=true
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                HELP=true
                shift
                ;;
            *)
                log_warning "未知参数: $1"
                shift
                ;;
        esac
    done
}

# 显示帮助信息
show_help() {
    cat << 'EOF'
Backend Smart Commit - 后端智能提交系统

用法:
    git-back-commit [选项]

选项:
    --dry-run, -n    试运行模式，只分析不提交
    --verbose, -v   详细输出模式
    --help, -h       显示此帮助信息

描述:
    基于Git diff快速扫描和分析后端服务代码变更，仅分析services/和packages/目录，
    避免前端代码干扰，实现秒级精准自动提交。

功能特性:
    • 后端域扫描 - 智能识别services/和packages/变更
    • Python语法检查 - 验证所有Python文件语法正确性
    • API兼容性检查 - 检测API端点变更的兼容性
    • 微服务关联分析 - 分析服务间依赖关系
    • 智能提交信息生成 - 按微服务分类生成标准化提交信息
    • 自动暂存和提交 - 智能暂存相关文件并执行git commit

示例:
    git-back-commit              # 自动分析和提交后端变更
    git-back-commit --dry-run    # 试运行模式，只分析不提交
    git-back-commit --verbose    # 详细输出模式

安全机制:
    • 语法验证失败时不会执行提交
    • 只处理后端文件，忽略前端变更
    • 自动暂存相关文件，避免遗漏
    • 标准化提交信息，便于团队协作

EOF
}

# 主函数
main() {
    # 解析参数
    parse_args "$@"

    # 显示帮助
    if [[ "$HELP" == true ]]; then
        show_help
        exit 0
    fi

    # 切换到仓库根目录
    cd "$REPO_ROOT"

    log_info "🚀 启动后端智能提交系统..."
    echo

    # 环境检查
    log_info "🔍 环境检查..."
    check_python
    check_git_repo
    check_python_script
    echo

    # 构建Python命令参数
    local python_args=""
    if [[ "$DRY_RUN" == true ]]; then
        python_args="$python_args --dry-run"
    fi

    if [[ "$VERBOSE" == true ]]; then
        python_args="$python_args --verbose"
    fi

    python_args="$python_args --repo-root $REPO_ROOT"

    # 执行Python脚本
    log_info "🔧 执行智能分析..."
    echo

    if python3 "$PYTHON_SCRIPT" $python_args; then
        echo
        log_success "🎉 后端智能提交完成！"

        if [[ "$DRY_RUN" == false ]]; then
            log_info "💡 提示: 如需回滚最近一次提交，请使用: git reset HEAD~1"
        fi
    else
        echo
        log_error "💥 后端智能提交失败！"
        log_info "💡 提示: 请检查错误信息并修复问题后重试"
        exit 1
    fi
}

# 执行主函数
main "$@"