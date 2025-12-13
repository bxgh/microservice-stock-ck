# Code Quality Report: [Story/Component Name]

**Story ID**: [Story编号]  
**检查日期**: [YYYY-MM-DD]  
**检查工具**: Ruff, Mypy, Pytest, Bandit  
**检查范围**: [src/xxx/, tests/xxx/]  
**总体评分**: [A/B/C/D]

---

## 📊 质量总览

| 检查项 | 状态 | 得分 | 详情 |
|--------|------|------|------|
| 代码风格 (Ruff) | ✅/⚠️/❌ | XX/100 | [链接](#代码风格检查) |
| 类型安全 (Mypy) | ✅/⚠️/❌ | XX/100 | [链接](#类型安全检查) |
| 测试覆盖率 | ✅/⚠️/❌ | XX% | [链接](#测试覆盖率) |
| 并发安全 | ✅/⚠️/❌ | - | [链接](#并发安全检查) |
| 性能测试 | ✅/⚠️/❌ | - | [链接](#性能测试) |
| 安全扫描 | ✅/⚠️/❌ | - | [链接](#安全扫描) |

**质量门控**: ✅ 通过 / ❌ 不通过

---

## 1️⃣ 代码风格检查

### 执行命令
```bash
ruff check src/ tests/
```

### 检查结果
**状态**: ✅ 通过 / ⚠️ 警告 / ❌ 失败

**统计**:
- 检查文件数: XX
- 发现问题: XX
- 严重问题: XX
- 警告: XX

### 问题详情

#### 问题1: [问题描述]
**文件**: [`src/path/file.py:123`](file:///path/to/file.py#L123)  
**类型**: [error/warning]  
**代码**: `E501`  
**说明**: Line too long (105 > 100 characters)

**修复建议**:
```python
# 修复前
very_long_line_that_exceeds_the_maximum_allowed_length_of_100_characters_and_needs_to_be_split()

# 修复后
very_long_line_that_needs_splitting(
    param1, param2, param3
)
```

**状态**: ✅ 已修复 / ⏳ 待修复

---

## 2️⃣ 类型安全检查

### 执行命令
```bash
mypy src/ --strict
```

### 检查结果
**状态**: ✅ 通过 / ⚠️ 警告 / ❌ 失败

**统计**:
- 检查文件数: XX
- 类型错误: XX
- 类型覆盖率: XX%

### 问题详情

#### 问题1: [问题描述]
**文件**: [`src/path/file.py:45`](file:///path/to/file.py#L45)  
**错误**: Missing type annotation for function return value

**修复建议**:
```python
# 修复前
async def fetch_data(code: str):
    return await self.client.get(code)

# 修复后
async def fetch_data(code: str) -> dict:
    return await self.client.get(code)
```

**状态**: ✅ 已修复 / ⏳ 待修复

---

## 3️⃣ 测试覆盖率

### 执行命令
```bash
pytest --cov=src --cov-report=term-missing
```

### 覆盖率统计
**整体覆盖率**: XX%  
**核心模块覆盖率**: XX%  
**状态**: ✅ 达标 (≥80%) / ❌ 未达标

### 模块覆盖率详情

| 模块 | 覆盖率 | 状态 | 未覆盖行 |
|------|--------|------|----------|
| `src/core/base.py` | XX% | ✅/❌ | L45-50, L78 |
| `src/adapters/provider.py` | XX% | ✅/❌ | L123-125 |

### 未覆盖代码分析

#### 模块: `src/core/base.py`
**未覆盖行**: L45-50

```python
# L45-50: 错误处理分支未测试
try:
    result = await operation()
except ConnectionError:  # 未覆盖
    logger.error("Connection failed")
    raise
```

**建议**:
```python
# 添加测试用例
async def test_connection_error_handling():
    with pytest.raises(ConnectionError):
        await base.operation()
```

**优先级**: 高/中/低

---

## 4️⃣ 并发安全检查

> ⚠️ **适用条件**: 代码涉及共享状态或多协程并发

### 并发安全分析

#### 检查点1: 共享状态保护
**文件**: [`src/core/pool.py`](file:///path/to/pool.py)  
**状态**: ✅ 正确使用Lock / ❌ 缺少Lock保护

```python
class ConnectionPool:
    def __init__(self):
        self._lock = asyncio.Lock()  # ✅ 正确
        self._connections = []
    
    async def get_connection(self):
        async with self._lock:  # ✅ 正确保护共享状态
            return self._connections.pop()
```

#### 检查点2: 并发测试验证
**测试文件**: [`tests/test_pool_concurrency.py`](file:///path/to/test.py)  
**状态**: ✅ 已实现 / ❌ 缺失

**测试场景**:
- [x] 多协程并发获取连接
- [x] 并发释放连接
- [x] Race condition检测

---

## 5️⃣ 性能测试

> ⚠️ **适用条件**: 性能关键路径（信号生成、API响应）

### 性能指标

| 指标 | 目标值 | 实际值 | 状态 |
|------|--------|--------|------|
| P50延迟 | < XXms | XXms | ✅/❌ |
| P95延迟 | < XXms | XXms | ✅/❌ |
| P99延迟 | < XXms | XXms | ✅/❌ |
| 吞吐量 | ≥ XXX/s | XXX/s | ✅/❌ |
| 内存峰值 | < XXX MB | XXX MB | ✅/❌ |

### 性能瓶颈分析
[如有性能问题，分析瓶颈原因]

**优化建议**:
- [优化建议1]
- [优化建议2]

---

## 6️⃣ 安全扫描

### 执行命令
```bash
bandit -r src/
```

### 扫描结果
**状态**: ✅ 无问题 / ⚠️ 有警告 / ❌ 有漏洞

**统计**:
- 扫描文件: XX
- 高危漏洞: XX
- 中危漏洞: XX
- 低危漏洞: XX

### 问题详情

#### 漏洞1: [漏洞描述]
**文件**: [`src/path/file.py:67`](file:///path/to/file.py#L67)  
**严重级别**: HIGH/MEDIUM/LOW  
**类型**: [漏洞类型，如硬编码密码]

**代码**:
```python
# 问题代码
password = "hardcoded_password"  # ❌ 安全风险
```

**修复建议**:
```python
# 从环境变量读取
password = os.getenv("DB_PASSWORD")
```

**状态**: ✅ 已修复 / ⏳ 待修复

---

## 📋 问题汇总

### 必须修复（阻塞合并）
| 优先级 | 问题 | 文件 | 状态 |
|--------|------|------|------|
| 🔴 P0 | [问题描述] | [文件:行号] | ⏳/✅ |

### 建议修复
| 优先级 | 问题 | 文件 | 状态 |
|--------|------|------|------|
| 🟡 P1 | [问题描述] | [文件:行号] | ⏳/✅ |

### 技术债务
- [ ] [技术债务1]
- [ ] [技术债务2]

---

## 🎯 改进建议

### 代码质量
- [改进建议1]
- [改进建议2]

### 测试策略
- [改进建议1]
- [改进建议2]

### 性能优化
- [优化建议1]
- [优化建议2]

---

## ✅ 质量门控结论

### 通过条件检查
- [ ] Ruff检查通过 (0 errors)
- [ ] Mypy类型检查通过 (0 errors)
- [ ] 测试覆盖率 ≥ 80%
- [ ] 并发测试通过（如适用）
- [ ] 性能测试达标（如适用）
- [ ] 无高危安全漏洞

### 最终结论
**状态**: ✅ 通过质量门控 / ❌ 不通过，需修复

**审核人**: [审核人]  
**审核日期**: [YYYY-MM-DD]

---

## 📎 附录

### 完整测试报告
[附加完整的pytest输出]

### 覆盖率报告
[附加完整的coverage报告]

---

*报告版本: 1.0*  
*生成工具: Antigravity AI + 自动化检查工具*  
*参考规范: QUALITY_GATE_CHECKLIST.md*
