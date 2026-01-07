# EPIC-016: 分布式分笔采集集群

## Epic 概述

| 字段 | 值 |
|------|-----|
| **Epic ID** | EPIC-016 |
| **标题** | 分布式分笔采集集群 (Distributed Tick Acquisition Cluster) |
| **优先级** | P1 |
| **状态** | 规划中 |
| **创建日期** | 2026-01-07 |
| **预计工期** | 4 天 |
| **来源** | 性能优化需求 |

---

## 1. 问题陈述

### 当前挑战
1. **采集耗时过长**: 全市场 5,293 只股票分笔采集需 80 分钟
2. **单机瓶颈**: 受限于单 IP 的 TDX 限流和带宽
3. **资源浪费**: 3 台服务器的 ClickHouse 集群已就绪，但采集仍为单机

### 业务影响
- 盘后数据延迟，影响策略复盘
- 无法满足 16:30 前完成采集的目标

---

## 2. 目标与成功指标

| 目标 | 指标 | 目标值 |
|------|------|--------|
| 缩短采集时间 | 全市场耗时 | ≤ 30 分钟 |
| 保持数据完整 | 成功率 | ≥ 98% |
| 利用集群资源 | 并发节点数 | 3 (41/58/111) |
| 09:25 覆盖率 | 有集合竞价数据 | ≥ 98% |

---

## 3. 架构方案

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Server 41  │     │  Server 58  │     │ Server 111  │
│  Shard 0    │     │  Shard 1    │     │  Shard 2    │
│  ~1766 股票 │     │  ~1766 股票 │     │  ~1761 股票 │
└─────┬───────┘     └──────┬──────┘     └──────┬──────┘
      │                    │                   │
      ▼                    ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ ClickHouse  │◄───►│ ClickHouse  │◄───►│ ClickHouse  │
│ Local Write │     │ Local Write │     │ Local Write │
└─────────────┘     └─────────────┘     └─────────────┘
        ↑ ReplicatedMergeTree 自动同步 ↑
```

**核心策略**: Hash 分片 (`hash(stock_code) % 3`)

---

## 4. 用户故事

### Story 16.1: gsd-worker 分片参数支持
**优先级**: P0 | **工时**: 2h

修改 `sync_tick.py` 支持 `--shard-index` 和 `--shard-total` 参数。

**验收标准**:
- [ ] 添加 `--shard-index` 和 `--shard-total` CLI 参数
- [ ] 实现 `hash(code) % total == index` 过滤逻辑
- [ ] 不传参时保持原有全量模式
- [ ] 单元测试覆盖分片逻辑

---

### Story 16.2: ClickHouse 本地写入配置
**优先级**: P0 | **工时**: 1h

修改 `TickSyncService` 支持从环境变量读取 ClickHouse 地址。

**验收标准**:
- [ ] `CLICKHOUSE_HOST` 环境变量生效
- [ ] 默认值为 `localhost`
- [ ] 测试本地写入功能

---

### Story 16.3: GitLab CI/CD 流水线
**优先级**: P0 | **工时**: 4h

配置 GitLab CI/CD 实现代码自动构建和多节点部署。

**验收标准**:
- [ ] 创建 `.gitlab-ci.yml`
- [ ] 配置 Docker Registry (58 服务器)
- [ ] 各服务器安装 GitLab Runner
- [ ] 配置 SSH 免密登录
- [ ] Push 后自动构建镜像
- [ ] 手动触发部署到各节点

---

### Story 16.4: Docker 部署配置
**优先级**: P1 | **工时**: 2h

创建各服务器的 Docker Compose 和环境配置。

**验收标准**:
- [ ] 创建 `docker-compose.yml` 模板
- [ ] 各节点 `.env` 配置 `SHARD_INDEX`
- [ ] `mootdx-api` 服务正常运行
- [ ] `gsd-worker` 可正确读取分片参数

---

### Story 16.5: 分布式任务调度
**优先级**: P1 | **工时**: 2h

配置 task-orchestrator 或脚本实现 3 节点并行触发。

**验收标准**:
- [ ] 创建 `scripts/distributed_tick_sync.sh`
- [ ] 并行 SSH 触发 3 节点采集
- [ ] 等待全部完成后汇总日志
- [ ] 集成到 crontab 或 task-orchestrator

---

### Story 16.6: 验证与文档
**优先级**: P1 | **工时**: 3h

执行全市场采集验证，更新相关文档。

**验收标准**:
- [ ] 全市场采集耗时 ≤ 30 分钟
- [ ] 数据完整性 ≥ 98%
- [ ] 各节点贡献约 1/3 数据
- [ ] 更新 `TICK_DATA_STANDARDS.md`
- [ ] 创建 `docs/operations/DISTRIBUTED_ACQUISITION.md`

---

## 5. 依赖关系

| 依赖项 | 状态 | 备注 |
|--------|------|------|
| ClickHouse 3 节点集群 | ✅ 已完成 | 41/58/111 |
| ReplicatedMergeTree 表 | ✅ 已完成 | tick_data |
| GitLab 安装 | ✅ 已完成 | 58 服务器 |
| 多节点连接池 | ✅ 已完成 | 今日完成 |
| Docker 环境 | ✅ 已完成 | 各服务器 |

---

## 6. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 分片不均匀 | 低 | 中 | Hash 函数保证均匀分布 |
| 单节点 mootdx-api 故障 | 中 | 中 | 健康检查 + 自动重启 |
| 网络分区 | 低 | 高 | ClickHouse 自动重试同步 |
| GitLab CI/CD 复杂 | 中 | 低 | 备选: 手动脚本部署 |

---

## 7. 实施计划

| 阶段 | Story | 时间 |
|------|-------|------|
| Day 1 | 16.1, 16.2 | 代码修改 |
| Day 2 | 16.3 | GitLab CI/CD |
| Day 3 | 16.4, 16.5 | 部署调度 |
| Day 4 | 16.6 | 验证文档 |

---

## 8. 关联文档

| 文档 | 用途 |
|------|------|
| [clickhouse-replicated-cluster.md](../architecture/clickhouse-replicated-cluster.md) | 集群架构 |
| [TICK_DATA_STANDARDS.md](../../services/task-orchestrator/docs/task_scheduling/TICK_DATA_STANDARDS.md) | 分笔规范 |
| [PERFORMANCE_TEST_TDX_POOL_20260107.md](../reports/PERFORMANCE_TEST_TDX_POOL_20260107.md) | 单机测试 |

---

*文档版本: 1.0*  
*最后更新: 2026-01-07*
