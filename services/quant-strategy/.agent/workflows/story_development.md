---
description: Story完整开发流程
---

# Story Development Workflow

本workflow定义Story从规划到交付的完整开发流程。

## 前置条件
- Story已在 `TASK_PROGRESS.md` 中定义
- 已明确Story的验收标准和依赖关系

---

## Phase 1: 技术设计

### 1.1 生成Implementation Plan
```bash
提示词: "请为Story [编号] [名称] 创建技术设计方案，使用templates/story_implementation_plan.md模板"
```

**必选动作**: 切换至 **Claude 4.5 Sonnet** (或模拟其思维模式) 进行深度分析

**交付物**: `docs/plans/stories/epic00X/story_X.X_implementation_plan.md`

### 1.2 人工审核设计方案
检查点:
- [ ] 数据模型设计合理
- [ ] API接口符合规范
- [ ] 考虑并发安全
- [ ] 符合编码标准

### 1.3 设计方案批准
**状态**: ✅ 批准 → 进入Phase 2 | ❌ 需修改 → 返回1.1

---

## Phase 2: 代码实现

### 2.1 创建文件结构
```bash
提示词: "根据implementation_plan创建Story [编号]的文件结构"
```

// turbo
```bash
# 创建必要的目录
mkdir -p src/new_module tests/new_module
```

### 2.2 实现核心代码
```bash
提示词: "实现Story [编号]的核心功能，严格遵循CODING_STANDARDS.md，包括:
- 完整的类型提示
- 完整的docstring
- 错误处理
- 并发安全（如需要）
- 资源管理（初始化和清理）"
```

**必选动作**: 根据代码类型切换模型
- 常规逻辑/CRUD → **GPT-4o** (速度优先)
- 核心架构/并发 → **Claude 4.5 Sonnet** (质量优先)
- 复杂算法/数学 → **o1** (推理优先)

---

## Phase 3: 质量检查

### 3.1 自动化质量检查
```bash
提示词: "对Story [编号]的代码执行质量检查，参考QUALITY_GATE_CHECKLIST.md"
```

执行以下检查（使用 code_quality_check.md workflow）:

// turbo-all
```bash
# 1. 代码风格
ruff check src/ tests/

# 2. 类型检查
mypy src/ --strict

# 3. 运行测试
docker compose -f docker-compose.dev.yml run --rm quant-strategy pytest --cov=src --cov-report=term-missing

# 4. 安全扫描
bandit -r src/
```

### 3.2 生成质量报告
```bash
提示词: "根据质量检查结果，生成质量报告，使用templates/quality_report.md模板"
```

**交付物**: `docs/qa/story_X.X_quality_report.md`

### 3.3 修复质量问题
如果质量检查未通过:
```bash
提示词: "根据质量报告修复所有P0问题"
```

**循环**: 修复 → 重新检查 → 直到通过

---

## Phase 4: 测试实现

### 4.1 单元测试生成
```bash
提示词: "为Story [编号]生成完整的单元测试，包括:
- 正常流程测试
- 边界条件测试
- 异常处理测试
目标覆盖率: ≥ 80%"
```

**AI模型推荐**: GPT-4o（快速生成）

### 4.2 并发测试（如适用）
如果代码涉及共享状态或并发访问:
```bash
提示词: "参考test_mootdx_connection_concurrency.py风格，为Story [编号]生成并发测试"
```

**必选动作**: 
- 常规测试 → **GPT-4o**
- 并发/复杂测试 → **Claude 4.5 Sonnet**

### 4.3 性能测试（如适用）
如果是性能关键路径:
```bash
提示词: "为Story [编号]生成性能测试，验证:
- 延迟指标 < [目标值]ms
- 吞吐量 ≥ [目标值]/s
- 内存使用稳定"
```

### 4.4 执行测试
// turbo
```bash
docker compose -f docker-compose.dev.yml run --rm quant-strategy pytest tests/ -v --cov=src --cov-report=html
```

**验收**: 所有测试通过 + 覆盖率达标

---

## Phase 5: 代码审查

### 5.1 AI代码审查
```bash
提示词: "对Story [编号]的代码进行深度审查，重点检查:
- 并发安全性（Lock使用、race condition）
- 资源管理（初始化、清理、异常处理）
- 时区处理（是否使用Asia/Shanghai）
- 性能优化机会
- 安全问题"
```

**必选动作**: 切换至 **Claude 4.5 Sonnet** 进行深度审查

### 5.2 人工审查
人工审查关键部分:
- [ ] 并发安全逻辑
- [ ] 资源释放逻辑
- [ ] 性能关键路径
- [ ] 安全敏感操作

---

## Phase 6: 文档更新

### 6.1 生成Walkthrough
```bash
提示词: "为Story [编号]生成walkthrough文档，使用templates/story_walkthrough.md模板，包括:
- 功能演示
- 测试结果
- 性能数据
- 代码亮点"
```

**交付物**: `docs/walkthroughs/story_X.X_walkthrough.md` 或 `brain/xxx/walkthrough.md`

### 6.2 更新项目文档
- [ ] 更新 `TASK_PROGRESS.md` (标记Story完成)
- [ ] 更新 API文档 (如有新API)
- [ ] 更新 README (如有重大功能)
- [ ] 创建进度报告 (重大Story需要)

### 6.3 更新Implementation Plan状态
在implementation_plan中标记:
- [x] 所有实现任务完成
- [x] 所有测试通过
- [x] 质量门控通过

---

## Phase 7: 代码交付 (Delivery)

### 7.1 清理环境
- 移除临时的测试文件或配置
- 确保 .gitignore 配置正确

### 7.2 Git提交
- 遵循Conventional Commits规范
- 格式: `feat(scope): descriptions`
- 示例: `feat(strategy): implement base strategy class for story 1.3`

### 7.3 通知用户
- 告知Story完成并已提交代码

---

## Phase 8: Story完成

### 8.1 最终验收
确认清单:
- [ ] 所有验收标准满足
- [ ] 质量门控通过
- [ ] 测试覆盖率达标
- [ ] 文档完整
- [ ] 代码已审查

### 8.2 标记Story完成
在 `TASK_PROGRESS.md` 中:
```markdown
### ✅ Story X.X: [Story名称] (已完成)
- [x] [任务1]
- [x] [任务2]

**交付文件**:
- `src/path/file.py`
- `docs/xxx/walkthrough.md`
```

---

## 快速参考

### 完整流程命令序列
```bash
# 1. 生成设计方案
AI: "为Story X.X创建技术设计"

# 2. 实现代码
AI: "实现Story X.X，遵循CODING_STANDARDS.md"

# 3. 质量检查
ruff check src/ && mypy src/ --strict

# 4. 运行测试
docker compose -f docker-compose.dev.yml run --rm quant-strategy pytest --cov=src

# 5. 生成walkthrough
AI: "为Story X.X生成walkthrough"

# 6. 更新文档
AI: "更新TASK_PROGRESS.md标记Story X.X完成"
```

### 相关文档
- [项目开发规范](../docs/standards/PROJECT_DEVELOPMENT_STANDARD.md)
- [AI模型选择指南](../docs/standards/AI_MODEL_SELECTION_GUIDE.md)
- [质量门控清单](../docs/standards/QUALITY_GATE_CHECKLIST.md)

---

*Workflow版本: 1.0*  
*维护者: 项目开发团队*
