# EPIC-013: 财务数据与统一访问层

## Epic 概述

| 字段 | 值 |
|------|-----|
| **Epic ID** | EPIC-013 |
| **标题** | 财务数据与统一访问层 (Financial Data & Unified Access Layer) |
| **优先级** | P1 |
| **状态** | 规划中 |
| **创建日期** | 2026-01-05 |
| **来源** | [FUTURE_DEVELOPMENT_PLAN.md](../ai_context/FUTURE_DEVELOPMENT_PLAN.md) |

---

## 1. 问题陈述

### 当前挑战
1. **关键字段缺失**: `major_shareholder_pledge_ratio` 在 API 中完全缺失
2. **财务同步未实现**: `weekly_financial_sync` 任务存在但 enabled: false
3. **估值同步未实现**: `monthly_valuation_sync` 任务未启用
4. **数据访问分散**: 策略需要分别调用 ClickHouse 和 MySQL

### 业务影响
- `PledgeRiskRule` 风控规则无法正常运行
- 策略缺少完整财务数据
- 数据访问代码重复，维护困难

---

## 2. 目标与成功指标

| 目标 | 指标 | 目标值 |
|------|------|--------|
| 数据完整性 | 财务字段覆盖率 | 100% |
| API 统一 | 单一入口调用 | FinancialDataProvider |
| 同步自动化 | weekly_financial_sync 成功率 | > 99% |
| 查询延迟 | P95 财务查询时间 | < 50ms |

---

## 3. 范围定义

### 本期范围 (W6-W8)
- `major_shareholder_pledge_ratio` 从 Baostock 采集
- `weekly_financial_sync` 实现并启用
- `monthly_valuation_sync` 实现并启用
- MySQL `stock_financial_latest` 表最新快照
- `FinancialDataProvider` 统一数据访问层
- Pydantic `FinancialIndicators` 统一模型

### 不在范围
- 因子计算存储（后续 EPIC）

---

## 4. 用户故事

### Story 13.1: major_shareholder_pledge_ratio 采集
**优先级**: P0  
实现从 Baostock 获取大股东质押率，写入 ClickHouse。

**验收标准**:
- [ ] 调用 Baostock `query_pledge_stat` 接口
- [ ] 数据写入 ClickHouse `stock_financial` 表
- [ ] `get_financial_indicators()` API 返回该字段

### Story 13.2: financial_sync 任务实现
**优先级**: P0  
完成 `weekly_financial_sync` 任务并启用。

**验收标准**:
- [ ] 每周六 06:00 自动触发
- [ ] 从 Baostock 获取最新财务报表
- [ ] 批量写入 ClickHouse

### Story 13.3: valuation_sync 任务实现
**优先级**: P1  
完成 `monthly_valuation_sync` 任务并启用。

**验收标准**:
- [ ] 每月 1 号 06:00 自动触发
- [ ] 从 Baostock 获取估值数据 (PE/PB/PS)
- [ ] 批量写入 ClickHouse

### Story 13.4: MySQL 最新快照表
**优先级**: P1  
创建 MySQL `stock_financial_latest` 表存储最新快照。

**验收标准**:
- [ ] 每日同步后更新 MySQL
- [ ] 表结构包含所有财务指标字段
- [ ] 主键为 stock_code

### Story 13.5: FinancialDataProvider 统一访问层
**优先级**: P0  
实现统一数据访问层，内部路由 ClickHouse ↔ MySQL。

**验收标准**:
- [ ] 历史聚合查询路由到 ClickHouse
- [ ] 最新单条查询路由到 MySQL
- [ ] 对上层策略透明

### Story 13.6: FinancialIndicators 统一模型
**优先级**: P1  
使用 Pydantic/Dataclass 定义统一数据模型。

**验收标准**:
- [ ] 包含所有财务指标字段
- [ ] 包含计算属性 (goodwill_ratio, cash_ratio 等)
- [ ] 文档清晰

### Story 13.7: 策略参数化管理
**优先级**: P1  
将所有策略阈值（PE、PB、ROE、质押率等）抽取到统一 YAML 配置。

**验收标准**:
- [ ] 创建 `config/strategies.yaml` 配置文件
- [ ] 实现 `StrategyConfigLoader` 配置加载器
- [ ] 策略初始化时自动读取参数
- [ ] 支持热更新（无需重启服务）

---

## 5. 依赖关系

| 依赖项 | 状态 | 备注 |
|--------|------|------|
| EPIC-012 完成 | 前置 | 同步机制就绪 |
| Baostock API 可用 | ✅ | 云端部署 |
| tasks.yml 配置 | ✅ 已有 | 需启用任务 |

---

## 6. 风险与缓解措施

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| Baostock 接口变更 | 低 | 高 | 接口版本锁定 + 告警 |
| 财务数据延迟发布 | 中 | 中 | 重试机制 + 备用数据源 |
| MySQL 写入瓶颈 | 低 | 低 | 批量 UPSERT |

---

## 7. 关联文档

| 文档 | 用途 |
|------|------|
| [STRATEGY_DATA_REQUIREMENTS.md](../ai_context/STRATEGY_DATA_REQUIREMENTS.md) | 数据缺口分析 |
| [tasks.yml](../../services/task-orchestrator/config/tasks.yml) | 任务配置 |
| [database-schema.md](../architecture/database-schema.md) | 表结构 |

---

*文档版本: 1.0*  
*最后更新: 2026-01-05*
