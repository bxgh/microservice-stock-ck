---
description: quant-strategy 开发规范检查流程 - 每个 Story 完成前必须执行
---

# Story 完成检查流程 (强制)

每个 Story 在宣布"完成"之前，**必须**完成以下检查项。

## 1. 代码实现检查

- [ ] 所有 I/O 操作使用 `async/await`
- [ ] 所有函数有类型提示
- [ ] 使用 SQLAlchemy ORM (非原始 SQL)
- [ ] 数据库配置指向腾讯云 MySQL (非本地 SQLite)

## 2. 测试要求 (核心)

// turbo-all

### 2.1 创建集成测试文件
```bash
# 测试文件必须存在
ls tests/test_<feature_name>.py
```

### 2.2 真实数据测试
```bash
# 在 Docker 环境运行测试 (禁止本地运行)
docker exec quant-strategy-dev pytest tests/test_<feature_name>.py -v
```

### 2.3 并发安全测试 (如使用 Lock)
如果代码中使用了 `asyncio.Lock()`，必须有并发测试验证。

## 3. API 验证

```bash
# 验证新增 API 端点可访问
curl http://localhost:8084/api/v1/<new_endpoint>
```

## 4. 完成标准

只有当以下条件**全部满足**时，Story 才算完成：

| 检查项 | 状态 |
|--------|------|
| 集成测试文件存在 | ☐ |
| 测试在 Docker 中通过 | ☐ |
| API 端点响应正确 | ☐ |
| 无硬编码密码 | ☐ |

## 5. 未通过处理

如果任一检查项未通过，**禁止**标记 Story 为完成。必须补齐后再提交。
