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

```需求
整理获取分笔数据的相关代码和任务，需要恢复盘后分笔数据的采集任务。
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
