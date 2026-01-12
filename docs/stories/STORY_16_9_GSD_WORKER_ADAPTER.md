# Story 16.9: GSD Worker 调度与入库适配

| 字段 | 值 |
|------|-----|
| **Story ID** | STORY-16.9 |
| **标题** | GSD Worker 调度与入库适配 |
| **关联 Epic** | EPIC-016 分布式分笔采集集群 |
| **优先级** | P1 |
| **工时预估** | 4h |

## 1. 描述
改造 `gsd-worker`，停止 HTTP 轮询，改为负责“发布任务”和“批量入库”。

## 2. 验收标准 (AC)
- [ ] **Job Publisher**: 
    - 实现 `publish_daily_jobs`，从数据库读取股票列表，生成 `post_market` 类型的任务推送到 Redis。
    - 支持全量发布 (5000+) 和 增量补漏发布。
- [ ] **Batch Writer**: 
    - 后台监听 `stream:tick:data`。
    - 实现 **Buffer 机制**: 满 20 只股票 或 满 1 秒，强制触发一次 ClickHouse 写入。
    - 确保写入无 `Too many parts` 报错。
- [ ] **清理旧代码**: 移除 `IntradayTickService` 中所有 `aiohttp` 相关逻辑。

## 3. 技术细节
- **Buffer 设计**: 使用 `List[TickData]` 暂存数据，配合 `asyncio.sleep(1)` loop 进行超时检查。
