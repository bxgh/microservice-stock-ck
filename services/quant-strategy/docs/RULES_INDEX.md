# 编码规范索引 (Rules Index)

**快速查找**: 使用 Ctrl+F 搜索关键词

---

## 📚 规范文档清单

| 文档 | 范围 | 优先级 | 位置 |
|------|------|--------|------|
| **CODING_STANDARDS.md** | 项目级规范 | ⭐⭐⭐ | `docs/CODING_STANDARDS.md` |
| python-coding-standards.md | 系统级Python规范 | ⭐⭐ | 用户定义规则 |
| quant-strategy-standards.md | 量化策略领域规范 | ⭐⭐ | 用户定义规则 |

---

## 🔍 按主题快速查找

### 测试相关
| 主题 | 规范 | 位置 |
|------|------|------|
| **真实数据优先** | 禁止Mock | CODING_STANDARDS.md §1 |
| 测试分层 | 单元/集成/性能 | CODING_STANDARDS.md §测试规范 |
| 覆盖率要求 | 核心≥90%, 工具≥80% | CODING_STANDARDS.md §覆盖率 |
| 并发测试 | 必须编写 | quant-strategy-standards.md |

### 性能相关
| 主题 | 指标 | 位置 |
|------|------|------|
| API响应时间 | P95 < 100ms | CODING_STANDARDS.md §性能指标 |
| 信号生成 | P95 < 200ms | CODING_STANDARDS.md §性能指标 |
| Redis缓存 | P95 < 10ms | CODING_STANDARDS.md §性能指标 |
| 吞吐量 | 10+并发策略 | CODING_STANDARDS.md §性能指标 |

### 代码质量
| 主题 | 要求 | 位置 |
|------|------|------|
| 异步优先 | 所有I/O用async/await | CODING_STANDARDS.md §3 |
| 类型提示 | 强制要求 | CODING_STANDARDS.md §4 |
| 资源管理 | try...finally | CODING_STANDARDS.md §5 |
| 并发安全 | asyncio.Lock() | CODING_STANDARDS.md §6 |
| 数据验证 | DataValidator | CODING_STANDARDS.md §7 |

### 安全相关
| 主题 | 要求 | 位置 |
|------|------|------|
| 密钥管理 | 禁止硬编码，使用环境变量 | CODING_STANDARDS.md §安全规范 |
| 敏感数据 | 日志脱敏 | CODING_STANDARDS.md §安全规范 |
| SQL注入 | 参数化查询 | CODING_STANDARDS.md §安全规范 |

### 日志规范
| 主题 | 要求 | 位置 |
|------|------|------|
| 日志级别 | DEBUG/INFO/WARNING/ERROR/CRITICAL | CODING_STANDARDS.md §日志规范 |
| 日志格式 | ISO时间戳 + extra上下文 | CODING_STANDARDS.md §日志规范 |
| 敏感信息 | mask_sensitive()脱敏 | CODING_STANDARDS.md §日志规范 |

### 错误处理
| 主题 | 要求 | 位置 |
|------|------|------|
| 错误分类 | 业务/系统/致命 | CODING_STANDARDS.md §错误处理 |
| 错误码 | 1xxx/2xxx/3xxx | CODING_STANDARDS.md §错误处理 |
| 错误消息 | 用户友好，无技术细节 | CODING_STANDARDS.md §错误处理 |

### 领域特定
| 主题 | 要求 | 位置 |
|------|------|------|
| 时区 | Asia/Shanghai (CST) | quant-strategy-standards.md |
| 交易时段 | 09:30-11:30, 13:00-15:00 | quant-strategy-standards.md |
| 技术栈 | FastAPI + Asyncio | quant-strategy-standards.md |

---

## 🚨 强制规则速查

### ⭐⭐⭐ P0 (违反禁止提交)
1. **禁止Mock数据** (集成测试)
2. **Docker容器测试** (所有测试)
3. **异步I/O** (async/await)
4. **类型提示** (所有函数)

### ⭐⭐ P1 (必须修复)
5. 资源管理 (try...finally)
6. 并发安全 (Lock)
7. 数据验证 (DataValidator)
8. **密钥管理** (禁止硬编码)
9. **敏感数据保护** (日志脱敏)
10. **错误分类处理** (业务/系统/致命)

### ⭐ P2 (建议遵守)
7. Git提交格式 (Conventional Commits)
8. Docstring格式

---

## 📖 常见场景指引

### 场景1: 编写新策略
**查阅规范**:
1. 测试分层 → `CODING_STANDARDS.md §测试规范`
2. 性能指标 → `CODING_STANDARDS.md §性能指标`
3. 时区处理 → `quant-strategy-standards.md`

### 场景2: 编写测试
**查阅规范**:
1. 真实数据优先 → `CODING_STANDARDS.md §1`
2. 测试分层 → `CODING_STANDARDS.md §测试规范`
3. 覆盖率要求 → `CODING_STANDARDS.md §覆盖率`

### 场景3: 性能优化
**查阅规范**:
1. 性能指标 → `CODING_STANDARDS.md §性能指标`
2. 并发安全 → `CODING_STANDARDS.md §5`

### 场景4: Code Review
**检查清单**:
- [ ] 是否使用真实数据测试？
- [ ] 是否有类型提示？
- [ ] 是否有资源释放？
- [ ] 是否线程安全？
- [ ] 性能是否达标？

---

## 🔄 更新日志

| 日期 | 变更 | 文档 |
|------|------|------|
| 2025-12-12 | 新增测试分层和性能指标 | CODING_STANDARDS.md |
| 2025-12-12 | 首次创建规范索引 | 本文档 |

---

**使用提示**: 
- 按 `Ctrl+F` 搜索关键词快速定位
- 优先查看 ⭐⭐⭐ 强制规则
- 不确定时查询"常见场景指引"
