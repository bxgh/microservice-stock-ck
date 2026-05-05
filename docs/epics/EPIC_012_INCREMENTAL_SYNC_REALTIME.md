# EPIC-012: 增量同步与实时行情

## Epic 概述

| 字段 | 值 |
|------|-----|
| **Epic ID** | EPIC-012 |
| **标题** | 增量同步与实时行情 (Incremental Sync & Realtime Quotes) |
| **优先级** | P0 |
| **状态** | 规划中 |
| **创建日期** | 2026-01-05 |
| **来源** | [FUTURE_DEVELOPMENT_PLAN.md](../ai_context/FUTURE_DEVELOPMENT_PLAN.md) |

---

## 1. 问题陈述

### 当前挑战
1. **K 线同步手动触发**: 缺乏自动化增量同步机制
2. **数据一致性验证缺失**: 同步后无 Verify-After-Write 校验
3. **服务无优雅停机**: 强停可致数据丢失 (TD-002)
4. **实时行情无落库**: Redis 缓存无持久化备份

### 业务影响
- K 线数据可能不完整
- 服务重启时数据丢失
- 无法进行历史分笔回测

---

## 2. 目标与成功指标

| 目标 | 指标 | 目标值 |
|------|------|--------|
| 同步自动化 | daily_kline_sync 成功率 | > 99% |
| 数据一致性 | Verify-After-Write 通过率 | 100% |
| 服务稳定性 | Graceful Shutdown 覆盖 | 100% 核心服务 |
| 实时落库 | tick 数据写入延迟 | < 1min |

---

## 3. 范围定义

### 本期范围 (W3-W5)
- `daily_kline_sync` 增量同步脚本
- Write-After-Verify 校验逻辑
- 自愈机制（不一致时自动重拉）
- gsd-worker / quant-strategy Graceful Shutdown
- 实时行情落库 (Redis → ClickHouse)

### 不在范围
- 云端分片并行同步（未来云部署）

---

## 4. 用户故事

### Story 12.1: 增量 K 线同步脚本
**优先级**: P0  
实现 `daily_kline_sync` 增量同步，每日 15:05 触发。

**验收标准**:
- [ ] 从云端 MySQL 增量读取当日 K 线
- [ ] 批量 INSERT INTO ClickHouse (batch_size=10000)
- [ ] 同步完成后记录到 Prometheus `sync_success_total`

### Story 12.2: Write-After-Verify 校验
**优先级**: P0  
实现同步后立即比对源/目标记录数。

**验收标准**:
- [ ] 同步后自动执行 COUNT(*) 校验
- [ ] 不一致时记录错误日志并触发告警
- [ ] 错误率指标上报 Prometheus

### Story 12.3: 自愈机制
**优先级**: P0  
发现不一致时自动删除本地分区并重新同步。

**验收标准**:
- [ ] 不一致触发 ALTER TABLE DROP PARTITION
- [ ] 自动重新拉取对应日期数据
- [ ] 自愈成功/失败记录日志

### Story 12.4: Graceful Shutdown 实现
**优先级**: P0  
gsd-worker 和 quant-strategy 实现优雅停机，关联 TD-002。

**验收标准**:
- [ ] SIGTERM 接收后完成当前任务再退出
- [ ] 连接池正确关闭
- [ ] 无数据丢失

### Story 12.5: 实时行情落库
**优先级**: P1  
实现 Redis 实时行情定期落库到 ClickHouse `stock_tick`。

**验收标准**:
- [ ] 每分钟聚合一次写入 ClickHouse
- [ ] 落库延迟 < 60s
- [ ] 支持历史分笔查询

---

## 5. 依赖关系

| 依赖项 | 状态 | 备注 |
|--------|------|------|
| EPIC-011 完成 | 前置 | 基础设施就绪 |
| tasks.yml daily_kline_sync | ✅ 已配置 | enabled: true |
| gsd-worker 镜像 | ✅ 已有 | 需增加优雅停机 |

---

## 6. 风险与缓解措施

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 云端 MySQL 同步超时 | 中 | 中 | 重试 + 21:00 超时告警 |
| 自愈导致数据短暂缺失 | 低 | 中 | 后台异步执行，不阻塞查询 |
| tick 落库过载 | 低 | 低 | 批量写入 + 限流 |

---

## 7. 关联文档

| 文档 | 用途 |
|------|------|
| [TECH_DEBT.md](../ai_context/TECH_DEBT.md) | TD-002 |
| [tasks.yml](../../services/task-orchestrator/config/tasks.yml) | 任务配置 |
| [STRATEGY_DATA_REQUIREMENTS.md](../ai_context/STRATEGY_DATA_REQUIREMENTS.md) | 数据需求 |

---

*文档版本: 1.0*  
*最后更新: 2026-01-05*
