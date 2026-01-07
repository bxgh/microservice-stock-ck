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

Critical Engineering Rules for Tick Data:
- **Strategy**: ALWAYS use **Sequential Batch Fetching (SBF)** moving backwards from 15:00 to 09:25.
- **Batch Size**: Use `batch_size=800` for stability. Larger batches (2k+) often fail or truncate.
- **Concurrency**: Set `concurrency=2` for full market sync to avoid IP bans and connection resets.
- **NaN Handling**: Always apply `df.where(pd.notnull(df), None)` before returning JSON to avoid 500 errors.
- **Resource Cleanup**: Add `await asyncio.sleep(0.25)` after closing `aiohttp.ClientSession` in `close()` methods.

```需求
目标: 确保分笔采集任务在全市场(5000+股票)规模下保持 100% 可用数据覆盖和高稳定性。
1. 使用 SBF 策略取代任何基于固定偏移或二分查找的逻辑。
2. 实现完善的重试机制 (至少 3 次，带指数退避)。
3. 确保 09:25 集合竞价数据的完整性。
```

## 🔗 核心文档路径

| 文档 | 路径 | 用途 |
|------|------|------|
| 采集规范 | `services/task-orchestrator/docs/task_scheduling/TICK_DATA_STANDARDS.md` | **必读 (SBF 详情)** |
| 常见问题 | `docs/ai_context/COMMON_PITFALLS.md` | **必读 (API 限制)** |
| 进度追踪 | `docs/ai_context/CURRENT_STATE.md` | 检查最近完成项 |
| 数据流向 | `docs/ai_context/DATA_FLOW.md` | SBF 回溯可视化 |
| 数据安全 | `docs/ai_collaboration/data_safety_policy.md` | 操作边界 |
