# Git 提交命令 (适用于 services 目录)

根据微服务 Git 工作流程，用于处理 Windows 环境下的编码问题。
此命令专门针对 services 目录的 git 仓库。

## 命令

```bash
# 1. 切换到 services 目录
cd services

# 2. 检查当前分支
git branch --show-current

# 3. 添加文件到暂存区
git add .

# 4. 检查状态
git status

# 5. 检查差异
git diff --staged

# 6. 创建提交消息文件 (避免命令行编码问题)
echo "feat(scope): 功能描述

- 核心功能点1
- 核心功能点2
- 测试情况

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>" > commit_message.txt

# 7. 使用文件方式提交
git commit -F commit_message.txt

# 8. 清理临时文件
rm commit_message.txt

# 9. 推送到远程 (如果需要)
# git push origin develop  # 开发分支
# git push origin main     # 主分支
# git push origin templates # 模板分支

# 10. 返回主目录 (可选)
# cd ..
```

## 分支策略

根据当前工作类型选择合适的分支：

### 开发新功能
```bash
git checkout develop
git checkout -b feature/service-name
# 开发完成后合并回 develop
```

### 更新模板
```bash
git checkout templates
# 修改模板...
git commit -m "feat(template): update with new features"
```

### 发布版本
```bash
git checkout main
git merge develop --no-ff
git tag -a v1.0.0 -m "Release version 1.0.0"
```

## 提交类型

使用约定式提交格式：

- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式化
- `refactor`: 重构代码
- `test`: 添加测试
- `chore`: 构建或辅助工具变动

### 示例
```bash
echo "feat(stock-data): add real-time data processing

- Implement WebSocket connection for live updates
- Add data validation and error handling
- Update API documentation

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>" > commit_message.txt
```

## 说明

此命令专门用于操作 `services` 目录的 git 仓库。

**重要提示：**
- 主目录没有 git 仓库，只有 `services` 目录有版本控制
- 执行此命令前请确保在项目根目录下
- 命令会自动切换到 `services` 目录进行 git 操作

**分支使用指南：**
- `main`: 生产环境稳定版本
- `develop`: 开发环境主分支
- `templates`: 微服务模板维护
- `feature/*`: 功能开发分支

在Windows环境下，直接使用 `git commit -m` 可能遇到编码问题，推荐使用文件方式提交。

这个命令序列会：

1. 自动切换到 `services` 目录
2. 显示当前分支信息
3. 暂存所有更改
4. 显示状态和差异以供审查
5. 创建格式化的提交消息
6. 使用文件方式提交（避免编码问题）
7. 清理临时文件
8. 可选推送到对应分支
9. 可选返回主目录
