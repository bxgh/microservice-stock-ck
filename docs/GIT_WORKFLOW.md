# Git 分支管理策略

## 🌳 分支结构

本项目采用标准的 Git 分支管理策略：

### **主要分支**

#### **`main`**
- 🎯 **用途**: 主分支，包含稳定的可发布代码
- 📝 **状态**: 生产就绪
- 🔒 **保护**: 禁止直接推送，只能通过 PR 合并
- 🚀 **来源**: 所有功能分支的目标

#### **`develop`** (未来创建)
- 🎯 **用途**: 开发分支，集成最新的功能
- 📝 **状态**: 开发中
- 🔄 **来源**: 功能分支合并到此
- 🎯 **目标**: 稳定后合并到 `main`

### **支持分支**

#### **`feature/*`**
- 🎯 **用途**: 功能开发
- 📝 **命名**: `feature/功能描述`
- 🔄 **来源**: 从 `main` 或 `develop` 分出
- 🎯 **目标**: 完成后 PR 到 `main` 或 `develop`

#### **`hotfix/*`** (未来)
- 🎯 **用途**: 紧急修复
- 📝 **命名**: `hotfix/问题描述`
- 🔒 **优先级**: 高优先级
- 🎯 **目标**: 修复后合并到 `main` 和 `develop`

## 📋 当前分支状态

```bash
# 当前活跃分支
* main                    # 主分支 (当前)
  feature/task-scheduler-frontend  # Task Scheduler前端功能分支
```

## 🚀 工作流程

### **1. 开发新功能**
```bash
# 从 main 创建功能分支
git checkout main
git pull origin main
git checkout -b feature/新功能名称

# 开发完成后
git add .
git commit -m "feat: 添加新功能描述"

# 推送到远程
git push origin feature/新功能名称

# 创建 Pull Request 到 main
```

### **2. 分支保护规则**

**main 分支**：
- ❌ 禁止直接推送
- ✅ 需要 Pull Request 审查
- ✅ 需要通过 CI/CD 检查
- ✅ 需要至少一个审查者批准

## 📝 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```bash
# 功能添加
git commit -m "feat: 添加用户登录功能"

# 问题修复
git commit -m "fix: 修复任务调度器内存泄漏"

# 文档更新
git commit -m "docs: 更新API文档"

# 样式调整
git commit -m "style: 调整按钮间距"

# 重构代码
git commit -m "refactor: 优化数据库查询逻辑"

# 性能优化
git commit -m "perf: 优化首页加载速度"

# 测试相关
git commit -m "test: 添加单元测试覆盖"

# 构建相关
git commit -m "build: 更新依赖版本"

# 回滚操作
git commit -m "revert: 回滚上一个版本"
```

## 🔄 分支切换最佳实践

### **切换到主分支**
```bash
git checkout main
git pull origin main  # 获取最新更新
```

### **切换到功能分支**
```bash
git checkout feature/task-scheduler-frontend
git pull origin feature/task-scheduler-frontend  # 获取最新更新
```

### **查看分支状态**
```bash
# 查看所有分支
git branch -a

# 查看当前分支状态
git status

# 查看分支差异
git diff main..feature/task-scheduler-frontend
```

## 🚨 常见问题

### **Q: 如何删除功能分支？**
```bash
# 删除本地分支
git branch -d feature/分支名称

# 强制删除本地分支（未合并）
git branch -D feature/分支名称

# 删除远程分支
git push origin --delete feature/分支名称
```

### **Q: 如何合并分支？**
```bash
# 合并到当前分支
git merge feature/源分支名称

# 变基（更清晰的提交历史）
git rebase main
```

### **Q: 如何处理分支冲突？**
1. `git status` 查看冲突文件
2. 手动编辑解决冲突
3. `git add` 标记已解决
4. `git commit` 完成合并

---

**文档维护**: 请在分支策略变更时更新此文档
**最后更新**: 2025-11-12
**版本**: v1.0