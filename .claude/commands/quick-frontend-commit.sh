#!/bin/bash

# Frontend Quick Git Commit Script
# 快速前端Git提交脚本

echo "🚀 Frontend Quick Commit"
echo "========================"

# 检查是否在git仓库中
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ 当前目录不是Git仓库"
    exit 1
fi

# 检查是否有更改
if [ -z "$(git status --porcelain)" ]; then
    echo "✅ 没有需要提交的更改"
    exit 0
fi

# 显示当前状态
echo ""
echo "📊 当前状态:"
git status --short

# 选择提交范围
echo ""
echo "🎯 选择提交范围:"
echo "1) 前端应用 (apps/frontend-web/)"
echo "2) 全部更改 (.)"
echo "3) 配置文件 (.claude/, package.json等)"
echo "4) 自定义输入"
read -p "选择 (1-4): " choice

case $choice in
    1)
        FILES="apps/frontend-web/"
        SCOPE="frontend"
        ;;
    2)
        FILES="."
        SCOPE="all"
        ;;
    3)
        FILES=".claude/ package*.json *.md .gitignore"
        SCOPE="config"
        ;;
    4)
        echo "输入文件路径 (用空格分隔):"
        read -e FILES
        SCOPE="custom"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

# 添加文件
echo ""
echo "📝 添加文件: $FILES"
git add $FILES

# 显示暂存状态
echo ""
echo "📋 暂存状态:"
git status --cached --short

# 选择提交类型
echo ""
echo "🏷️  提交类型:"
echo "1) feat     - 新功能"
echo "2) fix      - 修复"
echo "3) docs     - 文档"
echo "4) style    - 格式化"
echo "5) refactor - 重构"
echo "6) test     - 测试"
echo "7) chore    - 构建工具"
read -p "选择 (1-7): " type

case $type in
    1) TYPE="feat" ;;
    2) TYPE="fix" ;;
    3) TYPE="docs" ;;
    4) TYPE="style" ;;
    5) TYPE="refactor" ;;
    6) TYPE="test" ;;
    7) TYPE="chore" ;;
    *) TYPE="feat" ;;
esac

# 输入描述
echo ""
read -p "📝 输入提交描述: " DESC
if [ -z "$DESC" ]; then
    echo "❌ 描述不能为空"
    git reset
    exit 1
fi

# 创建提交消息
COMMIT_MSG="${TYPE}(${SCOPE}): ${DESC}

## 变更内容
- 主要功能实现或修复
- 影响的组件或页面

## 测试情况
- ✅ 功能正常
- ✅ 无控制台错误

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 确认提交
echo ""
echo "📋 提交信息预览:"
echo "$COMMIT_MSG" | head -5
echo "..."
read -p "确认提交? (Y/n): " confirm

if [[ $confirm =~ ^[Nn]$ ]]; then
    echo "❌ 取消提交"
    git reset
    exit 0
fi

# 执行提交
echo ""
echo "🔨 执行提交..."
echo "$COMMIT_MSG" | git commit -F -

if [ $? -eq 0 ]; then
    echo "✅ 提交成功!"
    echo "📊 提交信息: $(git log -1 --oneline)"

    # 询问推送
    read -p "🚀 推送到远程? (y/N): " push
    if [[ $push =~ ^[Yy]$ ]]; then
        BRANCH=$(git branch --show-current)
        echo "推送到分支: $BRANCH"
        git push origin $BRANCH
        if [ $? -eq 0 ]; then
            echo "✅ 推送成功!"
        else
            echo "❌ 推送失败"
        fi
    fi
else
    echo "❌ 提交失败"
    git reset
    exit 1
fi