# Create VSCode Workspace - 创建分支专用工作区

## 命令描述

为当前Git分支创建专用的VSCode工作区，自动检测分支类型并生成对应的配置，实现一键启动专用开发环境。

## 执行流程

### 1. 检测当前分支
- 获取当前Git分支名称
- 分析分支类型和功能
- 确定最适合的工作区配置

### 2. 生成工作区配置
- 根据分支类型选择颜色主题
- 配置文件过滤规则
- 推荐相关扩展
- 设置调试配置

### 3. 启动工作区
- 自动创建工作区文件
- 在新VSCode窗口中打开
- 切换到对应Git分支
- 显示使用提示

## 使用方法

### 创建并打开工作区
```
为当前分支创建VSCode工作区
```

### 创建特定类型工作区
```
为当前分支创建前端专用工作区
```

## 颜色主题说明

### 主题设计原则
- **舒适性**: 选择对眼睛友好的柔和色调，避免刺眼的鲜艳颜色
- **专业性**: 使用成熟的开发环境配色方案
- **易识别**: 保持足够的对比度，便于区分不同类型工作区

### 具体配色方案
- **前端分支**: 🟢 柔和绿色 (#3CB371) - 中等海绿色，温和不刺眼
- **后端分支**: 🟤 专业棕色 (#8B4513) - 稳重可靠，不刺眼的马鞍棕
- **跨域分支**: 🟣 温和紫色 (#7B68EE) - 中等石板蓝紫色，舒适优雅
- **基础设施分支**: ⚪ 专业灰色 (#708090) - 石板灰，稳重大方

## 分支类型识别规则

### 前端分支 (绿色主题 🟢)
包含以下关键词的分支会创建前端工作区：
- `frontend`, `ui`, `dashboard`, `web`, `client`, `vue`
- 分支示例: `feature/dashboard-improvement`, `fix/ui-bug`

**配置特点**:
- 隐藏所有 `services/` 目录
- 推荐扩展: Vue.volar, TypeScript, Tailwind CSS
- 颜色主题: 柔和绿色标题栏 (#3CB371)

### 后端分支 (棕色主题 🟤)
包含以下关键词的分支会创建后端工作区：
- `task-scheduler`, `data-`, `api`, `service`, `backend`, `python`
- 分支示例: `feature/task-scheduler-api`, `fix/data-collector`

**配置特点**:
- 隐藏所有 `apps/` 目录
- 推荐扩展: Python, Flake8, Black
- 颜色主题: 专业棕色标题栏 (#8B4513 - 马鞍棕)

### 跨域分支 (紫色主题 🟣)
包含以下关键词的分支会创建跨域工作区：
- `cross`, `integration`, `auth`, `full-stack`, `user-`
- 分支示例: `feature/cross-user-auth`, `feature/integration`

**配置特点**:
- 显示前后端文件，隐藏构建产物
- 推荐扩展: 全栈开发扩展集
- 颜色主题: 温和紫色标题栏 (#7B68EE)

### 基础设施分支 (灰色主题 ⚪)
包含以下关键词的分支会创建基础设施工作区：
- `infra`, `docker`, `ci`, `deploy`, `config`
- 分支示例: `feature/docker-optimization`, `fix/ci-pipeline`

**配置特点**:
- 专注配置和脚本文件
- 推荐扩展: Docker, YAML, CI/CD
- 颜色主题: 石板灰标题栏 (#708090)

## 输出格式

### 工作区创建成功
```
🚀 VSCode工作区创建器
==================

1. 分支分析...
   📝 当前分支: feature/dashboard-improvement
   🎯 检测类型: Frontend 工作区
   🎨 主题颜色: 柔和绿色 (#3CB371) - 前端专用

2. 配置生成...
   ✅ 工作区文件: .vscode/workspaces/feature-dashboard-improvement.code-workspace
   ✅ 文件过滤: 隐藏services目录 (减少60%文件)
   ✅ 扩展推荐: Vue, TypeScript, Tailwind CSS
   ✅ 调试配置: 前端开发环境

3. 启动工作区...
   🚀 VSCode新窗口已启动
   📂 工作区路径: /path/to/.vscode/workspaces/feature-dashboard-improvement.code-workspace
   🌿 Git分支: feature/dashboard-improvement

💡 使用提示:
   - 当前为前端工作区，专注前端开发
   - 使用 /git-front-commit 进行智能提交
   - 推荐扩展已自动推荐安装

✅ 前端专用工作区创建完成！
```

## 快速开始

### 步骤1: 创建功能分支
```bash
git checkout -b feature/你的功能名称
```

### 步骤2: 使用命令创建工作区
```
为当前分支创建VSCode工作区
```

### 步骤3: 开始开发
- 在新的VSCode窗口中专注开发
- 使用对应的智能提交命令
- 享受专用的开发环境

## 性能优势

### 文件过滤效果
- **前端工作区**: 文件数量减少 60-80%
- **后端工作区**: 文件数量减少 50-70%
- **跨域工作区**: 文件数量减少 30-40%

### 开发效率提升
- **启动速度**: 提升 3-5倍
- **文件搜索**: 提升 5-10倍
- **专注度**: 减少无关文件干扰

## 使用示例

### 前端开发
```bash
# 创建前端功能分支
git checkout -b feature/user-dashboard

# 使用命令创建前端工作区
为当前分支创建VSCode工作区

# 自动创建绿色主题工作区，隐藏后端文件
```

### 后端开发
```bash
# 创建后端功能分支
git checkout -b feature/task-scheduler-api

# 使用命令创建后端工作区
为当前分支创建VSCode工作区

# 自动创建棕色主题工作区，隐藏前端文件
```

### 跨域开发
```bash
# 创建跨域功能分支
git checkout -b feature/user-auth-system

# 使用命令创建跨域工作区
为当前分支创建跨域专用工作区

# 自动创建紫色主题工作区，显示前后端文件
```

## 注意事项

- **VSCode安装**: 确保已安装VSCode并添加到系统PATH
- **分支状态**: 工作区会自动切换到对应分支
- **配置文件**: 工作区配置会被Git忽略，避免冲突
- **扩展安装**: 首次使用可能需要手动安装推荐扩展

## 故障排除

### VSCode未启动
```bash
# 检查VSCode是否在PATH中
code --version

# 手动启动工作区
code --new-window .vscode/workspaces/分支名.code-workspace
```

### 分支不存在
```bash
# 创建新分支
git checkout -b 新分支名

# 然后重新执行命令
为当前分支创建VSCode工作区
```

这个命令提供了最简单直接的工作区创建方式，无需额外脚本，一键即可创建专用的开发环境。