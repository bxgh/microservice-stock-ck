#!/bin/bash

# VSCode分支工作区管理脚本
# 为不同分支创建专用的VSCode工作区

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT=$(cd "$(dirname "$0")/../.." && pwd)

# 帮助信息
show_help() {
    echo -e "${BLUE}VSCode分支工作区管理工具${NC}"
    echo ""
    echo "用法: $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  create-branch <branch-name> <service-type>  创建分支工作区"
    echo "  open-branch <branch-name>                   打开分支工作区"
    echo "  list-workspaces                            列出所有工作区"
    echo "  sync-branch <branch-name>                  同步分支到最新"
    echo "  cleanup                                    清理无用工作区"
    echo ""
    echo "服务类型:"
    echo "  frontend     - 前端开发工作区"
    echo "  backend      - 后端开发工作区"
    echo "  task-scheduler - Task Scheduler专用工作区"
    echo "  cross-domain - 跨域开发工作区"
    echo "  full         - 全栈开发工作区"
    echo ""
    echo "示例:"
    echo "  $0 create-branch feature/task-scheduler-cron-job task-scheduler"
    echo "  $0 create-branch feature/frontend-dashboard frontend"
    echo "  $0 open-branch feature/task-scheduler-cron-job"
}

# 创建工作区配置
create_workspace_config() {
    local branch_name=$1
    local service_type=$2
    local workspace_name="${branch_name//[^a-zA-Z0-9]/-}"

    echo -e "${BLUE}创建工作区配置: $workspace_name${NC}"

    # 根据服务类型创建工作区配置
    case $service_type in
        "frontend")
            cat > "$PROJECT_ROOT/.vscode/workspaces/$workspace_name.code-workspace" << EOF
{
  "name": "Frontend Development - $branch_name",
  "paths": ["${PROJECT_ROOT}"],
  "settings": {
    "workbench.colorCustomizations": {
      "titleBar.activeBackground": "#42b883",
      "titleBar.activeForeground": "#ffffff",
      "statusBar.background": "#35495e",
      "statusBar.foreground": "#ffffff"
    },
    "search.exclude": {
      "**/services": true,
      "**/node_modules": true,
      "**/dist": true,
      "**/build": true
    },
    "files.exclude": {
      "**/services": true,
      "**/node_modules": true,
      "**/.git": false
    },
    "typescript.preferences.importModuleSpecifier": "relative",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.eslint": true
    },
    "git.autofetch": true,
    "git.enableSmartCommit": true
  },
  "extensions": {
    "recommendations": [
      "Vue.volar",
      "Vue.vscode-typescript-vue-plugin",
      "bradlc.vscode-tailwindcss",
      "esbenp.prettier-vscode",
      "dbaeumer.vscode-eslint"
    ]
  },
  "tasks": {
    "version": "2.0.0",
    "tasks": [
      {
        "label": "Switch to Feature Branch",
        "type": "shell",
        "command": "git",
        "args": ["checkout", "$branch_name"],
        "group": "build",
        "presentation": {
          "echo": true,
          "reveal": "always",
          "focus": false,
          "panel": "shared"
        }
      }
    ]
  }
}
EOF
            ;;
        "backend")
            cat > "$PROJECT_ROOT/.vscode/workspaces/$workspace_name.code-workspace" << EOF
{
  "name": "Backend Development - $branch_name",
  "paths": ["${PROJECT_ROOT}"],
  "settings": {
    "git.branch": "$branch_name",
    "search.exclude": {
      "**/apps": true,
      "**/node_modules": true,
      "**/__pycache__": true,
      "**/.venv": true,
      "**/venv": true
    },
    "files.exclude": {
      "**/apps": true,
      "**/node_modules": true,
      "**/.git": false
    },
    "python.defaultInterpreterPath": "${PROJECT_ROOT}/services/task-scheduler/venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true
  },
  "extensions": {
    "recommendations": [
      "ms-python.python",
      "ms-python.flake8",
      "ms-python.black-formatter",
      "ms-python.debugpy"
    ]
  }
}
EOF
            ;;
        "task-scheduler")
            cat > "$PROJECT_ROOT/.vscode/workspaces/$workspace_name.code-workspace" << EOF
{
  "name": "Task Scheduler Development - $branch_name",
  "paths": ["${PROJECT_ROOT}"],
  "settings": {
    "git.branch": "$branch_name",
    "search.exclude": {
      "**/apps/frontend-web": true,
      "**/services/data-collector": true,
      "**/services/data-processor": true,
      "**/services/data-storage": true,
      "**/services/notification": true,
      "**/services/monitor": true,
      "**/services/api-gateway": true,
      "**/services/stock-data": true,
      "**/node_modules": true,
      "**/__pycache__": true
    },
    "files.exclude": {
      "**/apps/frontend-web": true,
      "**/services/data-collector": true,
      "**/services/data-processor": true,
      "**/services/data-storage": true,
      "**/services/notification": true,
      "**/services/monitor": true,
      "**/services/api-gateway": true,
      "**/services/stock-data": true,
      "**/.git": false
    },
    "python.defaultInterpreterPath": "${PROJECT_ROOT}/services/task-scheduler/venv/bin/python"
  },
  "extensions": {
    "recommendations": [
      "ms-python.python",
      "ms-python.flake8",
      "ms-python.black-formatter",
      "Vue.volar",
      "ms-vscode.vscode-typescript-next"
    ]
  },
  "launch": {
    "version": "0.2.0",
    "configurations": [
      {
        "name": "Debug Task Scheduler",
        "type": "python",
        "request": "launch",
        "program": "${PROJECT_ROOT}/services/task-scheduler/src/main.py",
        "console": "integratedTerminal",
        "cwd": "${PROJECT_ROOT}/services/task-scheduler"
      }
    ]
  }
}
EOF
            ;;
        "cross-domain")
            cat > "$PROJECT_ROOT/.vscode/workspaces/$workspace_name.code-workspace" << EOF
{
  "name": "Cross-Domain Development - $branch_name",
  "paths": ["${PROJECT_ROOT}"],
  "settings": {
    "git.branch": "$branch_name",
    "search.exclude": {
      "**/node_modules": true,
      "**/__pycache__": true,
      "**/.venv": true,
      "**/venv": true,
      "**/dist": true,
      "**/build": true
    },
    "files.exclude": {
      "**/node_modules": true,
      "**/__pycache__": true,
      "**/.venv": true,
      "**/venv": true,
      "**/.git": false
    }
  },
  "extensions": {
    "recommendations": [
      "ms-python.python",
      "ms-python.flake8",
      "ms-python.black-formatter",
      "Vue.volar",
      "Vue.vscode-typescript-vue-plugin",
      "bradlc.vscode-tailwindcss",
      "esbenp.prettier-vscode",
      "dbaeumer.vscode-eslint"
    ]
  },
  "launch": {
    "version": "0.2.0",
    "configurations": [
      {
        "name": "Debug Task Scheduler",
        "type": "python",
        "request": "launch",
        "program": "${PROJECT_ROOT}/services/task-scheduler/src/main.py",
        "cwd": "${PROJECT_ROOT}/services/task-scheduler"
      },
      {
        "name": "Debug Frontend Web",
        "type": "node",
        "request": "launch",
        "program": "${PROJECT_ROOT}/apps/frontend-web/node_modules/.bin/vite",
        "cwd": "${PROJECT_ROOT}/apps/frontend-web"
      }
    ],
    "compounds": [
      {
        "name": "Launch Full Stack",
        "configurations": ["Debug Task Scheduler", "Debug Frontend Web"],
        "stopAll": true
      }
    ]
  }
}
EOF
            ;;
        "full")
            cat > "$PROJECT_ROOT/.vscode/workspaces/$workspace_name.code-workspace" << EOF
{
  "name": "Full Stack Development - $branch_name",
  "paths": ["${PROJECT_ROOT}"],
  "settings": {
    "git.branch": "$branch_name",
    "search.exclude": {
      "**/node_modules": true,
      "**/__pycache__": true,
      "**/.venv": true,
      "**/venv": true,
      "**/dist": true,
      "**/build": true
    },
    "files.exclude": {
      "**/node_modules": true,
      "**/__pycache__": true,
      "**/.venv": true,
      "**/venv": true,
      "**/.git": false
    }
  }
}
EOF
            ;;
        *)
            echo -e "${RED}错误: 未知服务类型 '$service_type'${NC}"
            exit 1
            ;;
    esac

    echo -e "${GREEN}✅ 工作区配置创建成功${NC}"
}

# 创建分支工作区
create_branch_workspace() {
    local branch_name=$1
    local service_type=$2

    if [[ -z "$branch_name" || -z "$service_type" ]]; then
        echo -e "${RED}错误: 请提供分支名称和服务类型${NC}"
        exit 1
    fi

    # 确保工作区目录存在
    mkdir -p "$PROJECT_ROOT/.vscode/workspaces"

    # 创建工作区配置
    create_workspace_config "$branch_name" "$service_type"

    # 切换到目标分支
    echo -e "${BLUE}切换到分支: $branch_name${NC}"
    cd "$PROJECT_ROOT"
    git checkout "$branch_name" 2>/dev/null || git checkout -b "$branch_name"

    echo -e "${GREEN}✅ 分支工作区创建完成${NC}"
    echo -e "${YELLOW}💡 使用以下命令打开工作区:${NC}"
    echo -e "   $0 open-branch $branch_name"
}

# 打开分支工作区
open_branch_workspace() {
    local branch_name=$1
    local workspace_name="${branch_name//[^a-zA-Z0-9]/-}"
    local workspace_file="$PROJECT_ROOT/.vscode/workspaces/$workspace_name.code-workspace"

    if [[ ! -f "$workspace_file" ]]; then
        echo -e "${RED}错误: 工作区配置不存在 '$workspace_file'${NC}"
        echo -e "${YELLOW}💡 使用以下命令创建工作区:${NC}"
        echo -e "   $0 create-branch $branch_name <service-type>"
        exit 1
    fi

    echo -e "${BLUE}打开工作区: $branch_name${NC}"

    # 切换到目标分支
    cd "$PROJECT_ROOT"
    git checkout "$branch_name" 2>/dev/null || {
        echo -e "${YELLOW}分支不存在，创建新分支...${NC}"
        git checkout -b "$branch_name"
    }

    # 在新的VSCode实例中打开工作区
    code --new-window "$workspace_file"

    echo -e "${GREEN}✅ 工作区已在新的VSCode窗口中打开${NC}"
}

# 列出所有工作区
list_workspaces() {
    echo -e "${BLUE}可用的VSCode工作区:${NC}"

    local workspace_dir="$PROJECT_ROOT/.vscode/workspaces"

    if [[ ! -d "$workspace_dir" ]]; then
        echo -e "${YELLOW}  没有找到工作区配置${NC}"
        return
    fi

    for workspace_file in "$workspace_dir"/*.code-workspace; do
        if [[ -f "$workspace_file" ]]; then
            local workspace_name=$(basename "$workspace_file" .code-workspace)
            local display_name=$(grep -o '"name": "[^"]*"' "$workspace_file" | cut -d'"' -f4)
            local branch_name=$(grep -o '"git.branch": "[^"]*"' "$workspace_file" 2>/dev/null | cut -d'"' -f4 || echo "未知")

            echo "  - $workspace_name"
            echo "    名称: $display_name"
            echo "    分支: $branch_name"
            echo ""
        fi
    done
}

# 同步分支到最新
sync_branch() {
    local branch_name=$1

    if [[ -z "$branch_name" ]]; then
        echo -e "${RED}错误: 请提供分支名称${NC}"
        exit 1
    fi

    echo -e "${BLUE}同步分支: $branch_name${NC}"

    cd "$PROJECT_ROOT"

    # 保存当前分支
    local current_branch=$(git rev-parse --abbrev-ref HEAD)

    # 切换到main分支并更新
    git checkout main
    git pull origin main

    # 切换到目标分支并合并
    git checkout "$branch_name"
    if git merge main --no-edit; then
        echo -e "${GREEN}✅ 分支同步成功${NC}"
    else
        echo -e "${RED}❌ 合并冲突，请手动解决${NC}"
        return 1
    fi

    # 返回原分支
    git checkout "$current_branch"
}

# 清理无用工作区
cleanup() {
    echo -e "${BLUE}清理无用的VSCode工作区...${NC}"

    local workspace_dir="$PROJECT_ROOT/.vscode/workspaces"
    local removed_count=0

    for workspace_file in "$workspace_dir"/*.code-workspace; do
        if [[ -f "$workspace_file" ]]; then
            local branch_name=$(grep -o '"git.branch": "[^"]*"' "$workspace_file" 2>/dev/null | cut -d'"' -f4)

            # 检查分支是否还存在
            if [[ -n "$branch_name" ]] && ! git rev-parse --verify "$branch_name" >/dev/null 2>&1; then
                echo -e "${YELLOW}删除不存在分支的工作区: $(basename "$workspace_file" .code-workspace)${NC}"
                rm "$workspace_file"
                ((removed_count++))
            fi
        fi
    done

    echo -e "${GREEN}✅ 清理完成，删除了 $removed_count 个无用工作区${NC}"
}

# 主函数
main() {
    case $1 in
        "create-branch")
            create_branch_workspace $2 $3
            ;;
        "open-branch")
            open_branch_workspace $2
            ;;
        "list-workspaces")
            list_workspaces
            ;;
        "sync-branch")
            sync_branch $2
            ;;
        "cleanup")
            cleanup
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