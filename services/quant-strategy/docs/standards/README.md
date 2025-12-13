# 开发规范体系说明

**项目**: quant-strategy microservice  
**创建日期**: 2025-12-13  
**版本**: 1.0

---

## 📚 规范体系概述

本规范体系基于 **Antigravity AI协作能力** 和 **量化金融系统特殊要求**，为项目开发提供完整的指导框架。

### 体系目标
- ✅ 标准化开发流程
- ✅ 保证代码质量
- ✅ 提升开发效率
- ✅ 优化AI协作

---

## 📋 规范文档结构

```
docs/
├── standards/                        # 核心规范文档
│   ├── PROJECT_DEVELOPMENT_STANDARD.md    # 开发总规范 ⭐
│   ├── AI_MODEL_SELECTION_GUIDE.md        # AI模型选择
│   └── QUALITY_GATE_CHECKLIST.md          # 质量门控
├── templates/                        # 文档模板
│   ├── story_implementation_plan.md       # Story技术方案模板
│   ├── story_walkthrough.md               # Story验收演示模板
│   └── quality_report.md                  # 质量报告模板
├── TASK_PROGRESS.md                  # 项目进度总览
├── CODING_STANDARDS.md               # Python编码标准
└── antigravity_code_development_guide.md  # Antigravity通用指南

.agent/workflows/                     # 自动化工作流
├── story_development.md                   # Story开发流程
└── code_quality_check.md                  # 质量检查流程
```

---

## 🎯 核心规范文档

### 1. [项目开发规范](./standards/PROJECT_DEVELOPMENT_STANDARD.md) ⭐
**用途**: 定义完整的开发流程和标准

**包含内容**:
- 6个开发阶段定义
- AI模型选择建议
- 质量标准要求
- 快速启动命令

**何时使用**: 
- 开始新Story时阅读
- 作为开发过程参考

---

### 2. [AI模型选择指南](./standards/AI_MODEL_SELECTION_GUIDE.md)
**用途**: 指导在不同场景选择最优AI模型

**包含内容**:
- 4种模型能力对比
- 按开发阶段的模型推荐
- 量化策略项目专用建议
- 实战案例参考

**何时使用**:
- 开始技术设计时
- 需要代码审查时
- 实现复杂算法时

**典型场景**:
- 策略算法设计 → o1
- 异步代码审查 → Claude 4.5
- 快速CRUD开发 → GPT-4o
- 大规模重构 → Gemini 2.5 Pro

---

### 3. [质量门控清单](./standards/QUALITY_GATE_CHECKLIST.md)
**用途**: 定义强制质量标准

**包含内容**:
- 8项质量检查清单
- 自动化检查命令
- 质量报告模板
- 豁免机制

**何时使用**:
- 代码实现完成后
- 提交代码前
- 代码审查时

**核心检查项**:
1. ✅ Ruff代码风格 (0 errors)
2. ✅ Mypy类型检查 (严格模式)
3. ✅ 测试覆盖率 (≥ 80%)
4. ✅ 并发安全测试 (如适用)
5. ✅ 性能测试 (如适用)
6. ✅ 安全扫描 (无高危漏洞)

---

## 📝 文档模板

### 1. [Story Implementation Plan 模板](./templates/story_implementation_plan.md)
**用途**: Story技术设计方案

**使用方法**:
```bash
提示词: "为Story X.X创建技术设计，使用templates/story_implementation_plan.md模板"
```

**包含章节**:
- Story概述
- 需求分析
- 技术设计（架构、组件、API）
- 实现计划
- 测试策略
- 风险评估

---

### 2. [Story Walkthrough 模板](./templates/story_walkthrough.md)
**用途**: Story完成后的验收演示

**使用方法**:
```bash
提示词: "为Story X.X生成walkthrough，使用templates/story_walkthrough.md模板"
```

**包含章节**:
- Story概述
- 代码实现
- 质量保证结果
- 功能演示
- 性能测试结果
- 文档更新

---

### 3. [Quality Report 模板](./templates/quality_report.md)
**用途**: 代码质量检查报告

**使用方法**:
```bash
提示词: "根据质量检查结果生成报告，使用templates/quality_report.md模板"
```

**包含章节**:
- 质量总览
- 各项检查结果详情
- 问题汇总
- 改进建议
- 质量门控结论

---

## ⚙️ 自动化Workflow

### 1. [Story Development Workflow](./../.agent/workflows/story_development.md)
**用途**: Story完整开发流程

**7个Phase**:
1. 技术设计
2. 代码实现
3. 质量检查
4. 测试实现
5. 代码审查
6. 文档更新
7. Story完成

**使用方法**:
```bash
# 查看workflow
cat .agent/workflows/story_development.md

# 按workflow步骤执行
# 每个步骤都有明确的提示词和命令
```

---

### 2. [Code Quality Check Workflow](./../.agent/workflows/code_quality_check.md)
**用途**: 自动化质量检查流程

**6个Step**:
1. 代码风格检查 (Ruff)
2. 类型安全检查 (Mypy)
3. 单元测试与覆盖率
4. 并发安全检查 (条件)
5. 性能测试 (条件)
6. 安全扫描 (Bandit)

**使用方法**:
```bash
# 执行完整质量检查
docker compose -f docker-compose.dev.yml run --rm quant-strategy bash -c "
  ruff check src/ tests/ &&
  mypy src/ --strict &&
  pytest --cov=src --cov-report=term-missing -v &&
  bandit -r src/
"
```

**标注 `// turbo-all`**: workflow中所有命令都可自动执行

---

## 🚀 使用指南

### 新Story开发（完整流程）

#### Step 1: 创建Story
在 `TASK_PROGRESS.md` 中定义Story

#### Step 2: 技术设计
```bash
AI提示词: "为Story X.X创建技术设计，参考PROJECT_DEVELOPMENT_STANDARD.md和templates/story_implementation_plan.md"
```

#### Step 3: 代码实现
```bash
AI提示词: "实现Story X.X，严格遵循CODING_STANDARDS.md"
```

#### Step 4: 质量检查
```bash
# 执行 code_quality_check.md workflow
```

#### Step 5: 生成Walkthrough
```bash
AI提示词: "为Story X.X生成walkthrough，使用templates/story_walkthrough.md模板"
```

#### Step 6: 更新文档
```bash
AI提示词: "更新TASK_PROGRESS.md标记Story X.X完成"
```

---

### 快速参考卡片

| 场景 | 使用文档 | AI模型 |
|------|---------|--------|
| 开始新Story | PROJECT_DEVELOPMENT_STANDARD.md | - |
| 设计技术方案 | story_implementation_plan.md模板 | Claude |
| 选择AI模型 | AI_MODEL_SELECTION_GUIDE.md | - |
| 实现算法 | - | o1 |
| 快速开发 | - | GPT-4o |
| 代码审查 | QUALITY_GATE_CHECKLIST.md | Claude |
| 质量检查 | code_quality_check.md workflow | - |
| 生成演示 | story_walkthrough.md模板 | GPT-4o |

---

## 📊 规范遵循度追踪

### 当前Story质量指标
（示例，实际需要更新）

| Story | 设计方案 | 质量报告 | Walkthrough | 覆盖率 |
|-------|---------|----------|-------------|--------|
| 1.2 | ✅ | ✅ | ✅ | 75% |
| 1.3 | ⏳ | ⏳ | ⏳ | - |

### 团队目标
- [ ] 所有Story有implementation_plan
- [ ] 所有Story通过质量门控
- [ ] 测试覆盖率 ≥ 80%
- [ ] 所有Story有walkthrough

---

## 🔄 规范更新流程

### 规范版本控制
- 当前版本: 1.0
- 下次审查: 2025-12-31

### 更新原则
1. 基于实际项目反馈
2. 保持文档简洁
3. 与Antigravity能力同步
4. 适配量化策略需求

### 反馈机制
在Story walkthrough中记录:
- 规范哪些部分有帮助
- 哪些部分需要改进
- 新的最佳实践

---

## 🔗 外部参考

### Antigravity相关
- [Antigravity通用开发指南](./antigravity_code_development_guide.md)

### 项目专用
- [Python编码标准](./CODING_STANDARDS.md) (MEMORY)
- [量化策略标准](../../MEMORY/quant-strategy-standards.md) (MEMORY)

### 项目管理
- [任务进度跟踪](./TASK_PROGRESS.md)
- [EPIC规划](./plans/epics/)

---

## 💡 最佳实践

### DO ✅
- 每个Story都遵循完整流程
- 使用模板生成标准化文档，所有文档使用中文
- 质量门控失败时停止并修复
- 选择适合任务的AI模型
- 在walkthrough中总结经验教训

### DON'T ❌
- 跳过技术设计阶段
- 忽略质量门控结果
- 用o1做简单CRUD（浪费资源）
- 用GPT-4o做复杂并发审查（不够细致）
- 没有文档就标记Story完成

---

## 📞 获取帮助

### 遇到问题时
1. 查阅相关规范文档
2. 参考workflow步骤
3. 查看已完成Story的walkthrough作为示例
4. 咨询AI寻求建议

### 提示词模板
```bash
"根据[规范文档名]的要求，帮我[具体任务]"
```

---

*规范体系版本: 1.0*  
*创建日期: 2025-12-13*  
*维护者: 项目开发团队*  
*下次审查: 2025-12-31*
