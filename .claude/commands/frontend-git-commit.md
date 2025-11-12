# Frontend Git 提交命令

适用于前端项目的 Git 工作流程，基于 Monorepo 架构设计。
此命令专门针对前端开发工作，包括 apps/frontend-web 和相关配置。

## 命令

```bash
# 1. 检查当前项目状态
echo "=== Frontend Git 提交流程 ==="
echo "当前分支: $(git branch --show-current)"
echo "项目根目录: $(pwd)"

# 2. 检查是否有未提交的更改
if [ -z "$(git status --porcelain)" ]; then
    echo "✅ 没有需要提交的更改"
    exit 0
fi

# 3. 显示项目结构
echo ""
echo "=== 项目结构 ==="
echo "📁 apps/frontend-web/     - 前端应用"
echo "📁 apps/task-scheduler-ui/ - 任务调度UI (未来)"
echo "📁 packages/              - 共享包"
echo "📁 .claude/               - Claude配置"

# 4. 显示更改状态
echo ""
echo "=== Git 状态 ==="
git status --porcelain

# 5. 选择提交范围
echo ""
echo "=== 选择提交范围 ==="
echo "1) 全项目提交 (包括所有apps和packages)"
echo "2) 仅前端提交 (apps/frontend-web)"
echo "3) 选择性提交 (手动指定文件)"
read -p "请选择 (1-3): " scope

case $scope in
    1)
        echo "📝 准备提交全项目更改..."
        git add .
        SCOPE="all"
        ;;
    2)
        echo "📝 准备提交前端更改..."
        git add apps/frontend-web/
        SCOPE="frontend"
        ;;
    3)
        echo "📝 选择性提交模式"
        git status --porcelain | awk '{print $2}' | head -10
        read -p "输入要添加的文件 (用空格分隔): " files
        git add $files
        SCOPE="selected"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

# 6. 显示暂存的更改
echo ""
echo "=== 暂存的更改 ==="
git diff --staged --name-only

# 7. 确认提交
echo ""
read -p "确认提交? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "❌ 取消提交"
    git reset
    exit 1
fi

# 8. 选择提交类型
echo ""
echo "=== 提交类型 ==="
echo "1) feat    - 新功能"
echo "2) fix     - 修复bug"
echo "3) docs    - 文档更新"
echo "4) style   - 代码格式化"
echo "5) refactor - 重构"
echo "6) test    - 测试相关"
echo "7) chore   - 构建/工具"
read -p "请选择类型 (1-7): " type

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

# 9. 输入提交描述
echo ""
read -p "请输入提交描述: " description
if [ -z "$description" ]; then
    echo "❌ 提交描述不能为空"
    git reset
    exit 1
fi

# 10. 选择影响范围
echo ""
echo "=== 影响范围 ==="
echo "1) frontend       - 前端应用"
echo "2) dashboard      - 仪表板"
echo "3) components     - 组件库"
echo "4) api            - API集成"
echo "5) config         - 配置"
echo "6) build          - 构建"
echo "7) docs           - 文档"
read -p "请选择范围 (1-7): " area

case $area in
    1) AREA="frontend" ;;
    2) AREA="dashboard" ;;
    3) AREA="components" ;;
    4) AREA="api" ;;
    5) AREA="config" ;;
    6) AREA="build" ;;
    7) AREA="docs" ;;
    *) AREA="frontend" ;;
esac

# 11. 创建提交消息
COMMIT_MSG="${TYPE}(${AREA}): ${description}

## 主要变更
- 根据实际变更内容添加要点

## 技术细节
- 使用的相关技术和框架
- 影响的组件或页面

## 测试情况
- ✅ 本地开发服务器正常
- ✅ 组件渲染正常
- ✅ API调用正常
- ✅ 路由跳转正常

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 12. 创建提交消息文件
echo "$COMMIT_MSG" > .git_commit_message.txt

# 13. 执行提交
echo ""
echo "=== 执行提交 ==="
git commit -F .git_commit_message.txt

# 14. 清理临时文件
rm -f .git_commit_message.txt

# 15. 显示提交结果
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 提交成功!"
    echo "提交哈希: $(git rev-parse --short HEAD)"
    echo "提交信息: ${TYPE}(${AREA}): ${description}"

    # 询问是否推送
    read -p "是否推送到远程? (y/N): " push
    if [[ $push =~ ^[Yy]$ ]]; then
        CURRENT_BRANCH=$(git branch --show-current)
        echo "🚀 推送到分支: $CURRENT_BRANCH"
        git push origin $CURRENT_BRANCH
    fi
else
    echo "❌ 提交失败"
    git reset
    exit 1
fi
```

## 快捷提交脚本

### 前端快速提交
```bash
# 快速提交前端更改 (仅apps/frontend-web)
git add apps/frontend-web/
git commit -m "feat(frontend): 更新前端功能

- 具体变更内容
- 测试情况

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 组件库更新
```bash
git add apps/frontend-web/src/components/ apps/frontend-web/src/views/components/
git commit -m "feat(components): 更新组件库

- 新增/优化组件
- 更新示例页面
- 改进类型定义

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### API集成更新
```bash
git add apps/frontend-web/src/api/ apps/frontend-web/src/config/
git commit -m "feat(api): 更新API集成

- 新增微服务接口
- 优化错误处理
- 改进类型定义

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## 分支策略

### 功能开发
```bash
# 创建功能分支
git checkout -b feature/dashboard-monitoring

# 开发完成后
git checkout develop
git merge feature/dashboard-monitoring
git branch -d feature/dashboard-monitoring
```

### 紧急修复
```bash
# 从main分支创建hotfix
git checkout main
git checkout -b hotfix/critical-bug-fix

# 修复完成后合并回main和develop
git checkout main
git merge hotfix/critical-bug-fix
git checkout develop
git merge hotfix/critical-bug-fix
git branch -d hotfix/critical-bug-fix
```

## 提交类型规范

- **feat**: 新功能 (新页面、新组件、新API集成)
- **fix**: 修复bug (UI修复、逻辑错误、兼容性问题)
- **docs**: 文档更新 (README、API文档、组件文档)
- **style**: 代码格式化 (CSS样式、代码风格、格式调整)
- **refactor**: 重构 (代码优化、架构调整、性能改进)
- **test**: 测试相关 (单元测试、集成测试、E2E测试)
- **chore**: 构建工具 (依赖更新、配置文件、构建脚本)

## 影响范围

- **frontend**: 前端应用整体
- **dashboard**: 监控仪表板
- **components**: 组件库
- **api**: API集成和配置
- **config**: 配置文件
- **build**: 构建相关
- **docs**: 文档

## 使用说明

1. **执行前准备**:
   - 确保在项目根目录
   - 检查当前分支状态
   - 完成功能开发和测试

2. **选择合适提交范围**:
   - 全项目提交: 影响多个应用或包
   - 仅前端提交: 只涉及前端应用
   - 选择性提交: 特定文件或组件

3. **填写描述要求**:
   - 简洁明了，说明做了什么
   - 避免过于宽泛的描述
   - 包含必要的上下文信息

4. **提交后检查**:
   - 确认提交信息正确
   - 检查是否需要推送到远程
   - 更新相关文档或任务

## 示例提交消息

### 新功能提交
```bash
feat(dashboard): 添加微服务实时监控面板

- 集成ServiceManager进行API调用
- 实现健康检查和状态显示
- 添加服务网格和筛选功能
- 集成日志系统和实时更新

技术细节:
- Vue 3 Composition API
- Element Plus UI组件
- 响应式设计和暗色主题
- 微服务API集成

测试情况:
- ✅ 本地开发服务器正常
- ✅ 服务健康检查工作
- ✅ 实时数据更新正常
- ✅ 响应式布局适配
```

这个命令系统提供了完整的Git工作流程，适合前端开发的实际需求。