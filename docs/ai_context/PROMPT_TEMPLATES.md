# 🚀 新会话提示词模板

> 将以下内容复制到新会话的第一条消息中，帮助 AI 快速建立项目上下文。

---

## 模板 1: 标准开发任务

```
项目: microservice-stock (股票数据微服务平台)

开始任务前，请先阅读以下文档建立上下文:
1. docs/ai_context/QUICK_START.md - 项目概览和编码规范
2. docs/ai_context/SERVICE_REGISTRY.md - 服务列表和端口
3. docs/ai_context/COMMON_PITFALLS.md - 常见问题和教训

关键规范:
- 时区: Asia/Shanghai
- 异步: 全部使用 async/await
- 共享状态: 必须用 asyncio.Lock()
- 测试: 必须在 Docker 中运行: docker compose run --rm <service> pytest
- 端口/IP: 从 .env 或 docker-compose.yml 获取，不要凭记忆

任务: [描述你的任务]
```

---

## 模板 2: 调试/修复问题

```
项目: microservice-stock

请先阅读:
1. docs/ai_context/QUICK_START.md
2. docs/ai_context/COMMON_PITFALLS.md - 查看是否是已知问题

当前问题:
- 症状: [描述问题症状]
- 服务: [涉及的服务名]
- 错误日志: [粘贴关键错误信息]

请诊断问题并提出解决方案。
```

---

## 模板 3: 新功能开发

```
项目: microservice-stock

请先阅读:
1. docs/ai_context/QUICK_START.md
2. docs/ai_context/SERVICE_REGISTRY.md
3. docs/ai_context/DATA_FLOW.md - 理解数据流向
4. docs/ai_context/DECISION_LOG.md - 了解历史决策

新功能需求:
[描述需求]

注意事项:
- 遵循现有架构和编码规范
- 查阅 COMMON_PITFALLS.md 避免常见错误
- 任何数据修改操作需要先确认
```

---

## 模板 4: 代码质量检查 (QC)

```
项目: microservice-stock

请先阅读:
1. docs/ai_context/QUICK_START.md
2. .agent/rules/python-coding-standards.md - 编码规范
3. .agent/rules/quant-strategy-standards.md (如涉及策略)

请对以下服务进行代码质量检查:
- 服务: [服务名]
- 关注点: 异步安全、资源管理、错误处理

参考: .agent/workflows/code_quality_check.md
```

---

## 模板 5: 简短提醒版

```
项目: microservice-stock

必读: docs/ai_context/QUICK_START.md + COMMON_PITFALLS.md
规范: 时区 Asia/Shanghai, 异步优先, 共享状态加锁
测试: docker compose run --rm <service> pytest

任务: [任务描述]
```

---

## 📝 使用建议

1. **每次新会话都发送模板** — 确保 AI 有正确的上下文
2. **根据任务选择模板** — 不同任务类型使用不同模板
3. **包含具体信息** — 任务描述、错误日志等越具体越好
4. **提醒查阅文档** — 最重要的是 QUICK_START 和 COMMON_PITFALLS

---

## 🔗 核心文档路径

| 文档 | 路径 | 用途 |
|------|------|------|
| 快速入门 | `docs/ai_context/QUICK_START.md` | **必读** |
| 常见问题 | `docs/ai_context/COMMON_PITFALLS.md` | **必读** |
| 服务注册 | `docs/ai_context/SERVICE_REGISTRY.md` | 查端口/服务 |
| 数据流向 | `docs/ai_context/DATA_FLOW.md` | 理解数据路径 |
| 决策日志 | `docs/ai_context/DECISION_LOG.md` | 理解设计意图 |
| 技术债务 | `docs/ai_context/TECH_DEBT.md` | 避开雷区 |
| 数据安全 | `docs/ai_collaboration/data_safety_policy.md` | 操作边界 |
