# EPIC-011: 数据本地化基础设施

## Epic 概述

| 字段 | 值 |
|------|-----|
| **Epic ID** | EPIC-011 |
| **标题** | 数据本地化基础设施 (Data Localization Infrastructure) |
| **优先级** | P0 |
| **状态** | 规划中 |
| **创建日期** | 2026-01-05 |
| **来源** | [FUTURE_DEVELOPMENT_PLAN.md](../ai_context/FUTURE_DEVELOPMENT_PLAN.md) |

---

## 1. 问题陈述

### 当前挑战
1. **云端依赖**: 策略运行时依赖云端 MySQL 获取 K 线数据，网络延迟影响实时性
2. **隧道可靠性**: SSH 隧道 (GOST) 缺乏自动重连机制 (TD-003)
3. **Keeper 单点风险**: ClickHouse Keeper 仅 2 节点，单点故障风险 (TD-001)
4. **缓存层缺失**: 实时行情无本地缓存，重复查询浪费资源

### 业务影响
- K 线数据查询延迟 200ms+（跨网络）
- 隧道断开时策略扫描失败
- 无法支撑低延迟实时策略

---

## 2. 目标与成功指标

| 目标 | 指标 | 目标值 |
|------|------|--------|
| 降低数据延迟 | P95 查询时间 | < 50ms (本地 ClickHouse) |
| 提升可用性 | 数据层可用率 | 99.9% |
| 隧道稳定性 | 自动重连成功率 | > 99% |
| 缓存命中率 | 实时行情缓存 | > 80% |

---

## 3. 范围定义

### 本期范围 (W1-W2)
- ClickHouse 双主集群部署验证
- SSH 隧道 (GOST) 配置与自动重连
- Redis 缓存层配置
- 基础监控指标部署

### 不在范围
- Keeper 第 3 节点（待资源允许）
- 多租户数据隔离

---

## 4. 用户故事

### Story 11.1: ClickHouse 双主集群验证
**优先级**: P0  
验证 Server 41 与 Server 58 双主复制正常运行，确认 ReplicatedReplacingMergeTree 表结构。

**验收标准**:
- [ ] 两节点数据同步延迟 < 5s
- [ ] 单节点故障时另一节点可继续写入
- [ ] `system.replicas` 无异常标志

### Story 11.2: SSH 隧道自动重连
**优先级**: P0  
实现 GOST 隧道断开后自动重连机制，关联 TD-003。

**验收标准**:
- [ ] 隧道断开后 30s 内自动恢复
- [ ] 重连失败时触发告警
- [ ] 重连日志写入 Prometheus

### Story 11.3: Redis 缓存层配置
**优先级**: P1  
配置 Redis 实例用于实时行情缓存，TTL 策略配置。

**验收标准**:
- [ ] Redis 4GB 内存实例运行
- [ ] 实时行情 TTL = 5s
- [ ] 股票基本信息 TTL = 24h

### Story 11.4: 基础监控部署
**优先级**: P1  
部署 Prometheus 指标采集，Grafana 面板。

**验收标准**:
- [ ] ClickHouse 指标（CPU、内存、复制延迟）
- [ ] SSH 隧道连接状态
- [ ] Redis 内存使用率

---

## 5. 依赖关系

| 依赖项 | 状态 | 备注 |
|--------|------|------|
| ClickHouse 双主已部署 | ✅ 已完成 | Server 41 & 58 |
| Redis 已部署 | ✅ 已完成 | - |
| GOST 隧道已配置 | ✅ 已完成 | 需加重连机制 |
| Prometheus 已部署 | ✅ 已完成 | - |

---

## 6. 风险与缓解措施

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| Keeper 2 节点单点故障 | 中 | 高 | 监控 `is_session_expired`，人工介入；长期扩容至 3 节点 |
| 隧道频繁断开 | 低 | 中 | 自动重连 + 指数退避 |
| Redis 内存不足 | 低 | 中 | 监控 + TTL 清理 |

---

## 7. 关联文档

| 文档 | 用途 |
|------|------|
| [TECH_DEBT.md](../ai_context/TECH_DEBT.md) | TD-001, TD-003 |
| [clickhouse-replicated-cluster.md](../architecture/clickhouse-replicated-cluster.md) | 集群架构 |
| [FUTURE_DEVELOPMENT_PLAN.md](../ai_context/FUTURE_DEVELOPMENT_PLAN.md) | 规划来源 |

---

*文档版本: 1.0*  
*最后更新: 2026-01-05*
