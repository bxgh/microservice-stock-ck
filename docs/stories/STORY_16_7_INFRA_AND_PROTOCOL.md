# Story 16.7: Redis Stream 基础设施与协议定义

| 字段 | 值 |
|------|-----|
| **Story ID** | STORY-16.7 |
| **标题** | Redis Stream 基础设施与协议定义 |
| **关联 Epic** | EPIC-016 分布式分笔采集集群 |
| **优先级** | P0 (Blocker) |
| **工时预估** | 2h |

## 1. 描述
在开始代码重构前，必须先确立 Redis Streams 的基础环境和通信协议。本 Story 负责定义 Key Schema、消息体 JSON 格式，并封装统一的 Python SDK 供两端调用。

## 2. 验收标准 (AC)
- [ ] **Redis Key 规范**: 
    - 任务流: `stream:tick:jobs` (MAXLEN=10000)
    - 数据流: `stream:tick:data` (MAXLEN=50000)
    - 消费者组: `group:mootdx:workers`
- [ ] **Job Protocol**: 定义并实现 `TickJob` 数据类 (Pydantic)，包含 `job_id`, `stock_code`, `type` (post_market/intraday)。
- [ ] **Result Protocol**: 定义并实现 `TickResult` 数据类，包含 `status`, `data_blob`, `0925_check`。
- [ ] **SDK 封装**: 提供 `RedisStreamClient` 基础类，封装 `xadd`, `xreadgroup`, `xack` 等底层操作。

## 3. 技术细节
- 需要确保 Redis 版本支持 Streams (5.0+)。
- 消息体使用 JSON 序列化，数据 Blob 使用 gzip 压缩 (可选，视大小而定)。
