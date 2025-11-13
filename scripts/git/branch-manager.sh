#!/bin/bash

# 微服务并行开发分支管理脚本
# 用于创建和管理微服务特性分支

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服务列表
SERVICES=("task-scheduler" "data-collector" "data-processor" "data-storage" "notification" "monitor" "api-gateway" "stock-data")
FRONTENDS=("frontend-web" "task-scheduler-front")

# 显示帮助信息
show_help() {
    echo -e "${BLUE}微服务并行开发分支管理工具${NC}"
    echo ""
    echo "用法: $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  create-service <service-name> <branch-name>  创建服务特性分支"
    echo "  create-frontend <frontend-name> <branch-name> 创建前端特性分支"
    echo "  create-cross <branch-name>                    创建跨域特性分支"
    echo "  list-services                                列出所有可用服务"
    echo "  list-branches                                列出当前特性分支"
    echo "  merge <branch-name>                          合并特性分支"
    echo "  sync                                         同步主分支"
    echo ""
    echo "示例:"
    echo "  $0 create-service task-scheduler feature/add-cron-job"
    echo "  $0 create-frontend frontend-web feature/ui-improvement"
    echo "  $0 create-cross feature/user-auth-system"
}

# 验证服务名称
validate_service() {
    local service=$1
    if [[ " ${SERVICES[@]} " =~ " ${service} " ]]; then
        return 0
    else
        echo -e "${RED}错误: 未知服务 '$service'${NC}"
        echo -e "${YELLOW}可用服务: ${SERVICES[*]}${NC}"
        return 1
    fi
}

# 验证前端名称
validate_frontend() {
    local frontend=$1
    if [[ " ${FRONTENDS[@]} " =~ " ${frontend} " ]]; then
        return 0
    else
        echo -e "${RED}错误: 未知前端 '$frontend'${NC}"
        echo -e "${YELLOW}可用前端: ${FRONTENDS[*]}${NC}"
        return 1
    fi
}

# 创建服务特性分支
create_service_branch() {
    local service=$1
    local branch_name=$2

    validate_service $service || exit 1

    local full_branch_name="feature/${service}-${branch_name}"

    echo -e "${BLUE}创建服务特性分支: $full_branch_name${NC}"

    # 确保在最新代码上
    git fetch origin
    git checkout main
    git pull origin main

    # 创建新分支
    git checkout -b $full_branch_name

    # 创建分支配置文件
    mkdir -p .git/branch-info
    cat > .git/branch-info/current.json << EOF
{
  "branch_type": "service",
  "service": "$service",
  "branch_name": "$branch_name",
  "created_at": "$(date -Iseconds)",
  "affected_dirs": ["services/$service"]
}
EOF

    echo -e "${GREEN}✅ 成功创建分支: $full_branch_name${NC}"
    echo -e "${YELLOW}💡 提示: 使用 /git-back-commit 进行后端代码提交${NC}"
}

# 创建前端特性分支
create_frontend_branch() {
    local frontend=$1
    local branch_name=$2

    validate_frontend $frontend || exit 1

    local full_branch_name="feature/${frontend}-${branch_name}"

    echo -e "${BLUE}创建前端特性分支: $full_branch_name${NC}"

    # 确保在最新代码上
    git fetch origin
    git checkout main
    git pull origin main

    # 创建新分支
    git checkout -b $full_branch_name

    # 创建分支配置文件
    mkdir -p .git/branch-info
    cat > .git/branch-info/current.json << EOF
{
  "branch_type": "frontend",
  "frontend": "$frontend",
  "branch_name": "$branch_name",
  "created_at": "$(date -Iseconds)",
  "affected_dirs": ["apps/$frontend"]
}
EOF

    echo -e "${GREEN}✅ 成功创建分支: $full_branch_name${NC}"
    echo -e "${YELLOW}💡 提示: 使用 /git-front-commit 进行前端代码提交${NC}"
}

# 创建跨域特性分支
create_cross_branch() {
    local branch_name=$1
    local full_branch_name="feature/cross-${branch_name}"

    echo -e "${BLUE}创建跨域特性分支: $full_branch_name${NC}"

    # 确保在最新代码上
    git fetch origin
    git checkout main
    git pull origin main

    # 创建新分支
    git checkout -b $full_branch_name

    # 创建分支配置文件
    mkdir -p .git/branch-info
    cat > .git/branch-info/current.json << EOF
{
  "branch_type": "cross-domain",
  "branch_name": "$branch_name",
  "created_at": "$(date -Iseconds)",
  "affected_dirs": ["apps/", "services/", "packages/"]
}
EOF

    echo -e "${GREEN}✅ 成功创建跨域分支: $full_branch_name${NC}"
    echo -e "${YELLOW}💡 提示: 使用 /git-cross-commit 进行跨域代码提交${NC}"
}

# 列出所有服务
list_services() {
    echo -e "${BLUE}可用的后端服务:${NC}"
    for service in "${SERVICES[@]}"; do
        echo "  - $service"
    done
    echo ""
    echo -e "${BLUE}可用的前端应用:${NC}"
    for frontend in "${FRONTENDS[@]}"; do
        echo "  - $frontend"
    done
}

# 列出当前特性分支
list_branches() {
    echo -e "${BLUE}当前特性分支:${NC}"

    # 获取所有feature分支
    git fetch origin
    local branches=$(git branch -r | grep "origin/feature/" | sed 's/origin\///' | grep -v HEAD)

    if [[ -z "$branches" ]]; then
        echo -e "${YELLOW}  没有找到特性分支${NC}"
        return
    fi

    echo "$branches" | while read branch; do
        # 获取分支信息
        local info=""
        if [[ -f ".git/branch-info/current.json" ]]; then
            local current_branch=$(git rev-parse --abbrev-ref HEAD)
            if [[ "$current_branch" == "$branch" ]]; then
                info=" (当前分支)"
            fi
        fi

        echo "  - $branch$info"
    done
}

# 同步主分支
sync_main() {
    echo -e "${BLUE}同步主分支...${NC}"

    # 保存当前分支
    local current_branch=$(git rev-parse --abbrev-ref HEAD)

    # 切换到main分支并更新
    git checkout main
    git fetch origin
    git pull origin main

    # 返回原分支
    git checkout $current_branch

    # 尝试合并main分支
    echo -e "${YELLOW}尝试合并main分支到当前分支...${NC}"
    if git merge main --no-edit; then
        echo -e "${GREEN}✅ 主分支同步成功${NC}"
    else
        echo -e "${RED}❌ 合并冲突，请手动解决${NC}"
        return 1
    fi
}

# 合并特性分支
merge_branch() {
    local branch_name=$1

    if [[ -z "$branch_name" ]]; then
        echo -e "${RED}错误: 请指定要合并的分支名称${NC}"
        return 1
    fi

    echo -e "${BLUE}合并特性分支: $branch_name${NC}"

    # 检查分支是否存在
    if ! git rev-parse --verify "origin/$branch_name" >/dev/null 2>&1; then
        echo -e "${RED}错误: 分支 '$branch_name' 不存在${NC}"
        return 1
    fi

    # 切换到main分支
    git checkout main
    git pull origin main

    # 合并特性分支
    if git merge "origin/$branch_name" --no-edit; then
        echo -e "${GREEN}✅ 分支合并成功${NC}"

        # 推送到远程
        git push origin main

        # 询问是否删除特性分支
        echo -e "${YELLOW}是否删除特性分支 '$branch_name'? (y/N)${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            git push origin --delete "$branch_name"
            echo -e "${GREEN}✅ 已删除特性分支${NC}"
        fi
    else
        echo -e "${RED}❌ 合并冲突，请手动解决${NC}"
        return 1
    fi
}

# 主函数
main() {
    case $1 in
        "create-service")
            create_service_branch $2 $3
            ;;
        "create-frontend")
            create_frontend_branch $2 $3
            ;;
        "create-cross")
            create_cross_branch $2
            ;;
        "list-services")
            list_services
            ;;
        "list-branches")
            list_branches
            ;;
        "sync")
            sync_main
            ;;
        "merge")
            merge_branch $2
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            echo -e "${RED}错误: 未知命令 '$1'${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"