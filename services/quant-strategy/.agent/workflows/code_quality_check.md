---
description: 代码质量自动化检查流程
---

# Code Quality Check Workflow

本workflow执行完整的代码质量检查，用于Story开发过程中的质量门控。

## 适用场景
- Story代码实现后的质量检查
- 合并前的最终检查
- 定期代码质量审计

---

## 前置条件
- 代码已提交到本地
- Docker环境正常运行
- 已安装所有依赖包

---

## 检查流程

### Step 1: 代码风格检查

// turbo
```bash
# 使用Ruff检查代码风格
ruff check src/ tests/
```

**期望结果**: `All checks passed!`

**如有错误**: 自动修复
```bash
ruff check --fix src/ tests/
```

---

### Step 2: 类型安全检查

// turbo
```bash
# 使用Mypy检查类型
mypy src/ --strict
```

**期望结果**: `Success: no issues found`

**常见问题修复**:
- 缺少类型提示: 添加函数参数和返回值类型
- 隐式Optional: 明确标注 `Optional[Type]`
- Any类型滥用: 使用具体类型

---

### Step 3: 单元测试与覆盖率

// turbo
```bash
# 在Docker环境中运行测试
docker compose -f docker-compose.dev.yml run --rm quant-strategy \
  pytest --cov=src --cov-report=term-missing --cov-report=html -v
```

**期望结果**: 
- 所有测试通过
- 核心模块覆盖率 ≥ 80%

**覆盖率报告位置**: `htmlcov/index.html`

---

### Step 4: 并发安全检查（条件执行）

**触发条件**: 代码涉及共享状态或并发访问

// turbo
```bash
# 运行并发测试
docker compose -f docker-compose.dev.yml run --rm quant-strategy \
  pytest tests/ -k "concurrency" -v
```

**期望结果**: 所有并发测试通过，无race condition

---

### Step 5: 性能测试（条件执行）

**触发条件**: 性能关键路径代码

// turbo
```bash
# 运行性能测试
docker compose -f docker-compose.dev.yml run --rm quant-strategy \
  pytest tests/ -k "performance" -v
```

**期望结果**: 所有性能指标达标

---

### Step 6: 安全扫描

// turbo
```bash
# 使用Bandit扫描安全漏洞
bandit -r src/
```

**期望结果**: 无高危漏洞

**允许的例外**: 低危警告（需在报告中说明）

---

## 质量报告生成

### 汇总检查结果
```bash
提示词: "根据以上检查结果，生成质量报告，使用templates/quality_report.md模板"
```

AI会自动:
1. 汇总所有检查结果
2. 识别需要修复的问题
3. 提供修复建议
4. 生成完整的质量报告

**交付物**: `docs/qa/story_X.X_quality_report.md`

---

## 质量门控判定

### 通过条件
- ✅ Ruff检查: 0 errors
- ✅ Mypy检查: 0 errors (严格模式)
- ✅ 测试覆盖率: ≥ 80% (核心模块)
- ✅ 所有测试通过
- ✅ 并发测试通过 (如适用)
- ✅ 性能测试达标 (如适用)
- ✅ 无高危安全漏洞

### 不通过处理
如果任何检查失败:
1. AI生成修复建议
2. 修复代码
3. 重新运行检查
4. 循环直到通过

---

## 快速执行（一键检查）

### 完整检查命令
// turbo
```bash
docker compose -f docker-compose.dev.yml run --rm quant-strategy bash -c "
  echo '=== 1. Code Style Check ===' &&
  ruff check src/ tests/ &&
  echo &&
  echo '=== 2. Type Check ===' &&
  mypy src/ --strict &&
  echo &&
  echo '=== 3. Tests & Coverage ===' &&
  pytest --cov=src --cov-report=term-missing -v &&
  echo &&
  echo '=== 4. Security Scan ===' &&
  bandit -r src/ -ll
"
```

---

## 相关文档
- [质量门控清单](../docs/standards/QUALITY_GATE_CHECKLIST.md)
- [编码标准](../docs/CODING_STANDARDS.md)
- [质量报告模板](../docs/templates/quality_report.md)

---

*Workflow版本: 1.0*  
*维护者: 项目开发团队*
