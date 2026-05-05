# 未来开发规划（AI Context）

## 目标概述
- **实现完整的数据本地化**：财务、行情、估值数据在本地 ClickHouse 与 MySQL 双库同步，满足低延迟、批量回测与实时策略的双重需求。
- **提供 AI Agent 可直接使用的统一接口**：通过 `FinancialDataProvider` 抽象层，AI Agent 能透明获取历史聚合或最新快照。
- **保障系统可靠性与可观测性**：监控、告警、自愈机制、审计日志全链路覆盖。

## 阶段划分 & 关键里程碑

| 阶段 | 周次 | 关键任务 | 产出 | 依赖 |
|------|------|----------|------|------|
| **准备阶段** | W1‑W2 | - ✅ 部署 ClickHouse 三节点集群<br>- ✅ 搭建 SSH‑Tunnel (GOST)<br>- ✅ 配置 Redis | 集群部署文档、隧道配置、Redis 实例 | 3 台服务器 (8CPU/64GB/2TB) |
| **增量同步实现** | W3‑W4 | - 开发 `daily_kline_sync` 增量脚本<br>- 实现 Write‑After‑Verify 与自愈逻辑<br>- 实现 Graceful Shutdown (TD-002)<br>- 添加 Prometheus 指标 | Docker 镜像、CI 测试、监控仪表盘 | gsd-worker 镜像 |
| **实时行情落库** | W5 | - 实现 `realtime_quote_sync`（Redis 缓存 + ClickHouse 落库）<br>- 编写秒级落库批处理 | 代码、性能基准报告 | Redis 实例 |
| **财务/估值同步** | W6‑W7 | - 完成 `financial_sync`（每日全量/增量）<br>- **实现 `major_shareholder_pledge_ratio` 采集 + API**<br>- 将最新快照写入 MySQL `stock_financial_latest` | MySQL 表结构、同步脚本、文档更新 | Baostock API |
| **统一数据访问层** | W8 | - 实现 `FinancialDataProvider`（内部路由 ClickHouse ↔ MySQL）<br>- 添加 Pydantic/Dataclass `FinancialIndicators` 统一模型 | Python 包、单元测试 | - |
| **自愈机制验证** | W9‑W10 | - ✅ Weekly Deep Audit **已实现** (tasks.yml)<br>- 验证自愈触发逻辑<br>- 完善 `audit_logs` 表写入 | 验证报告、告警规则 | - |
| **全链路压测 & 优化** | W11‑W12 | - 并发 500 QPS 压测<br>- 调优 ClickHouse 分区、TTL、批写参数<br>- **双主故障切换演练** | 性能报告、调优配置 | - |
| **文档完善** | W13 | - 完成《数据本地化方案》文档<br>- 编写运维手册、故障恢复流程 | 文档 | - |

> **备注**: `daily_strategy_scan` 已在 tasks.yml 启用（18:30 交易日），依赖 `daily_kline_sync`。

## 资源保障

### 硬件资源
| 资源 | 配置 | 用途 |
|------|------|------|
| **ClickHouse 集群** | 3 台物理服务器 (41/58/111)。S41/S58 为单网卡，**S111 已扩容至三网卡 (全隔离)**。配置：8-16 核 CPU，64GB 内存，2TB NVMe SSD | 三节点复制集群，存储历史行情、财务和估值数据 |
| **MySQL 数据库** | 1 台腾讯云虚拟机，4 核 CPU，16GB 内存，500GB SSD | 云端数据采集节点 |
| **GOST 隧道服务器** | 集成于 Server 41 | SSH 隧道，本地 36301 → 云端 26300 |
| **Redis 缓存** | 1 台虚拟机，4GB 内存 | 实时行情缓存、异步任务队列 |

### 网络与安全
- **流量分流系统**：Server 111 已实现内网同步流与外网采集流物理隔离
- **内部专线**：1Gbps 物理专线 (目标升级至 10Gbps)
- **SSH 隧道加密**：GOST 建立的 SSH 隧道（本地 36301 → 云端 26300）
- **防火墙策略**：仅放行必要端口，ClickHouse 仅允许内部 127.0.0.1 访问
- **最小权限原则**：MySQL 只读权限，ClickHouse 最小权限
- **审计日志**：所有关键操作写入 ClickHouse `audit_logs` 表

### 监控与告警
- **Prometheus + Grafana**：系统指标和业务指标可视化
- **Alertmanager**：通过 Slack/钉钉实时告警
- **关键指标**：`sync_success_total`、`sync_latency_seconds`、`is_session_expired`

## 风险与缓解

| 风险 | 影响 | 缓解措施 | 关联 |
|------|------|----------|------|
| ~~ClickHouse Keeper 仅 2 节点~~ | ✅ **已解决** (2026-01-07 扩容至 3 节点) | Raft 2/3 多数派，任意 1 节点故障可自动切换 | ~~TD-001~~ |
| 云端 MySQL 不可达 | 同步中断，策略失去最新 K 线 | 双通道（MySQL + Baostock API）备份；任务超时自动回滚 | - |
| ClickHouse 磁盘耗尽 | 写入失败，数据不完整 | 预留 30% 余量，TTL 自动清理 180 天前数据 | - |
| SSH 隧道不稳定 | 延迟增大、任务超时 | GOST 自动重连 + 指数退避；超时告警 | TD-003 |
| 审计日志写入瓶颈 | 监控失效 | 异步批写（Redis 队列 → 后台批处理） | - |
| 代码变更导致字段缺失 | 策略误判 | CI 中加入 Schema 检查，缺失字段阻止部署 | - |
| 服务缺少 Graceful Shutdown | 强停可致数据丢失 | 在 W3-W4 阶段实现优雅停机 | TD-002 |

## 已知限制

| 限制 | 影响 | 状态 |
|------|------|------|
| ~~ClickHouse Keeper 仅 2 节点~~ | ~~无法满足 Raft 多数派~~ | ✅ **已解决** (2026-01-07) |

## 交付物清单

| 优先级 | 交付物 |
|--------|--------|
| **P0** | ClickHouse 表结构（`stock_financial`、`stock_kline_daily`、`audit_logs`）<br>MySQL 表结构（`stock_financial_latest`）<br>同步脚本（`daily_kline_sync.py`、`financial_sync.py`） |
| **P1** | 统一访问层 `FinancialDataProvider`<br>`major_shareholder_pledge_ratio` API<br>Prometheus 指标 & Grafana 面板配置 |
| **P2** | 实时行情同步脚本（`realtime_quote_sync.py`）<br>完整《数据本地化方案》文档<br>运维手册、故障恢复流程 |

## EPIC 分解

| EPIC ID | 标题 | 优先级 | 周次 |
|---------|------|--------|------|
| [EPIC-011](../epics/EPIC_011_DATA_LOCALIZATION_INFRASTRUCTURE.md) | 数据本地化基础设施 | P0 | W1-W2 |
| [EPIC-012](../epics/EPIC_012_INCREMENTAL_SYNC_REALTIME.md) | 增量同步与实时行情 | P0 | W3-W5 |
| [EPIC-013](../epics/EPIC_013_FINANCIAL_DATA_UNIFIED_ACCESS.md) | 财务数据与统一访问层 | P1 | W6-W8 |
| [EPIC-014](../epics/EPIC_014_SYSTEM_VERIFICATION_DOCUMENTATION.md) | 系统验证与文档完善 | P1 | W9-W13 |
| [EPIC-015](../epics/EPIC_015_LONG_TERM_PLATFORM_ENHANCEMENT.md) | 长期规划 - 平台能力扩展 | P2 | 2026-02 起 |

## 相关文档

| 文档 | 内容 |
|------|------|
| [TECH_DEBT.md](./TECH_DEBT.md) | 技术债务清单（TD-001、TD-002、TD-003） |
| [CURRENT_STATE.md](./CURRENT_STATE.md) | 项目当前状态 |
| [STRATEGY_DATA_REQUIREMENTS.md](./STRATEGY_DATA_REQUIREMENTS.md) | 策略数据需求与缺口分析 |
| [clickhouse-replicated-cluster.md](../architecture/infrastructure/clickhouse-replicated-cluster.md) | ClickHouse 三节点集群架构 |
| [tasks.yml](../../services/task-orchestrator/config/tasks.yml) | 任务调度配置 |

---

*更新时间: 2026-01-08*
