# Story 16.8: Mootdx Service 核心重构 (Worker模式)

| 字段 | 值 |
|------|-----|
| **Story ID** | STORY-16.8 |
| **标题** | Mootdx Service 核心重构 (Worker模式) |
| **关联 Epic** | EPIC-016 分布式分笔采集集群 |
| **优先级** | P0 (Core) |
| **工时预估** | 6h |

## 1. 描述
将 `mootdx-service` 改造为事件驱动的 Worker。它需要并发从 Redis 领取任务，并执行“100%成功率”的矩阵搜索算法。

## 2. 验收标准 (AC)
- [ ] **RedisStreamWorker**: 实现主循环，支持并发处理 (Semaphore限制并发数，如 10)。
- [ ] **SearchStrategy 移植**: 
    - 完整移植 `真正100%成功_修复版.py` 中的 `proven_search_matrix`。
    - 实现 `verify_0925()` 校验逻辑，必须返回 <=09:25 的数据。
    - 实现 `drop_duplicates` 和 `sort_values` 清洗逻辑。
- [ ] **异常处理**: 
    - 遇到网络错误自动重试。
    - 采集失败时推送 `status: failed` 消息。
- [ ] **资源池对接**: 正确使用 `TDXClientPool` 获取连接。

## 3. 技术细节
- **类结构**:
    - `workers/stream_worker.py`: 负责 Redis 交互。
    - `core/search_strategy.py`: 负责 TDX 交互和算法。
- **并发**: 使用 `asyncio.create_task` 分发任务。
