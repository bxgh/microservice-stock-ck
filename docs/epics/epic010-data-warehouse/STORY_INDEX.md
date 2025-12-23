# EPIC-010 Story 索引

## Story 列表

| Story ID | 标题 | 优先级 | 预估工时 | 状态 |
|----------|------|--------|----------|------|
| [10.0](./stories/STORY_10.0_DATA_COLLECTOR_SCAFFOLD.md) | data-collector 服务脚手架 | P0 | 3 天 | ⏳ 待开始 |
| [10.1](./stories/STORY_10.1_CLICKHOUSE_SCHEMA.md) | ClickHouse 表结构设计 | P0 | 2 天 | ⏳ 待开始 |
| [10.2](./stories/STORY_10.2_KLINE_COLLECTOR.md) | 日K线采集任务 | P0 | 3 天 | ⏳ 待开始 |
| [10.3](./stories/STORY_10.3_FINANCIALS_COLLECTOR.md) | 财务数据采集任务 | P0 | 3 天 | ⏳ 待开始 |
| [10.4](./stories/STORY_10.4_DATA_WAREHOUSE_SCAFFOLD.md) | data-warehouse 服务脚手架 | P1 | 3 天 | ⏳ 待开始 |
| [10.5](./stories/STORY_10.5_UNIFIED_API.md) | 统一数据访问 API | P1 | 4 天 | ⏳ 待开始 |
| [10.6](./stories/STORY_10.6_FACTOR_STORAGE.md) | 因子存储集成 | P1 | 3 天 | ⏳ 待开始 |
| [10.7](./stories/STORY_10.7_REALTIME_COLLECTOR.md) | 实时行情采集 | P2 | 4 天 | ⏳ 待开始 |

---

## 依赖关系图

```
[10.0 data-collector 脚手架]
        |
        ├── [10.1 ClickHouse 表结构] ────┬── [10.2 日K线采集]
        |                               └── [10.3 财务采集]
        |
        └── [10.7 实时行情采集]

[10.1 ClickHouse 表结构]
        |
        └── [10.4 data-warehouse 脚手架]
                |
                └── [10.5 统一 API]
                        |
                        └── [10.6 因子存储]
```

---

## 实施阶段

| 阶段 | 时长 | 包含 Story | 目标 |
|------|------|-----------|------|
| **Phase 1** | 2 周 | 10.0, 10.1, 10.2, 10.3 | 数据采集基础 |
| **Phase 2** | 2 周 | 10.4, 10.5 | 数据访问层 |
| **Phase 3** | 2 周 | 10.6, 10.7 | 因子与实时 |

---

## 总工时估算

- **P0 Story**: 11 天
- **P1 Story**: 10 天
- **P2 Story**: 4 天
- **总计**: 约 25 个工作日 (5 周)

---

*创建日期: 2025-12-23*
