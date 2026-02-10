# EPIC-GSF: 通用量化策略分析框架 (General Strategy Framework)

**版本**: v1.0  
**状态**: 📝 规划中  
**创建日期**: 2026-02-08  
**负责团队**: quant-strategy

---

## 1. 背景与目标

### 1.1 背景
当前系统已积累多种量化分析需求：
- **日K级别**：次新股多维对标、发行价溢价分析、Beta/流动性画像
- **Tick级别**：OFI订单失衡、VPIN知情交易、Lead-Lag龙头跟随、Smart Money大单追踪

这些策略共享大量底层逻辑（数据加载、特征计算、报告生成），但缺乏统一框架导致代码重复、维护困难。

### 1.2 目标
构建一个**可扩展的模块化策略框架**，满足：
1. **分层解耦**：DAO / Analyzer / Orchestrator 三层分离
2. **统一接口**：所有分析器遵循 `IAnalyzer` 协议
3. **多粒度支持**：同时支持日K和Tick级别数据
4. **策略注册**：支持动态注册新策略引擎

---

## 2. 架构概览

```
┌─────────────────────────────────────────────┐
│ Strategy Registry (策略注册表)             │
└─────────────────────────────────────────────┘
                       │
┌─────────────────────────────────────────────┐
│ Orchestrator Layer (编排层)                 │
│  SubNewBenchmarkEngine | LeadLagEngine      │
└─────────────────────────────────────────────┘
                       │
┌─────────────────────────────────────────────┐
│ Analyzer Layer (分析层 - 纯逻辑)            │
│  VolatilityAnalyzer | DrawdownAnalyzer      │
│  BetaCalculator | OFIAnalyzer | VPINCalc    │
└─────────────────────────────────────────────┘
                       │
┌─────────────────────────────────────────────┐
│ DAO Layer (数据访问层)                      │
│  StockInfoDAO | KLineDAO | TickDAO          │
│  IndustryDAO | FeatureDAO                   │
└─────────────────────────────────────────────┘
```

---

## 3. 分阶段实施计划

### Part 0: mootdx-source 扩展 (前置依赖)
- 文档: [epic_mds_extension.md](file:///home/bxgh/microservice-stock/services/mootdx-source/docs/epic_mds_extension.md)
- 目标: 扩展 mootdx-source 支持新数据类型
- 范围: DATA_TYPE_ISSUE_PRICE, DATA_TYPE_SW_INDUSTRY, DATA_TYPE_FEATURES

### Part 1: DAO Layer 基础设施
- 文档: [epic_gsf_part_1_dao.md](./epic_gsf_part_1_dao.md)
- 目标: 完成数据访问层的 gRPC 客户端封装
- 范围: `DataSourceClient`, `StockInfoDAO`, `IndustryDAO`, `KLineDAO`, `PeerSelector`

### Part 2: Analyzer Layer 核心分析器
- 文档: [epic_gsf_part_2_analyzer.md](./epic_gsf_part_2_analyzer.md)
- 目标: 实现日K级别的6个分析器
- 范围: Volatility, Drawdown, Multiples, Beta, Liquidity, Recovery

### Part 3: Orchestrator Layer + Sub-New Benchmark
- 文档: [epic_gsf_part_3_orchestrator.md](./epic_gsf_part_3_orchestrator.md)
- 目标: 完成次新股对标引擎的完整闭环
- 范围: `SubNewBenchmarkEngine`, `ReportAggregator`

### Part 4: 通用扩展 (Tick DAO + Strategy Registry)
- 文档: [epic_gsf_part_4_extension.md](./epic_gsf_part_4_extension.md)
- 目标: 扩展框架支持Tick级别策略
- 范围: `TickDAO`, `FeatureDAO`, `StrategyRegistry`

---

## 4. 验收标准

| 阶段 | 核心验收指标 |
|:---|:---|
| Part 1 | DAO 能成功从 MySQL 获取 issue_price 和 申万行业 |
| Part 2 | 所有 Analyzer 通过单元测试 (无 IO 依赖) |
| Part 3 | 688802 对标报告能成功生成 |
| Part 4 | 新增策略可通过 Registry 动态注册 |

---

## 5. 相关文档

- [次新股对标策略规范](file:///home/bxgh/.gemini/antigravity/brain/78fe721d-8836-4b28-8050-3094176916ce/implementation_plan.md)
- [tick_quant_strategy_pipeline](file:///home/bxgh/.gemini/antigravity/knowledge/tick_quant_strategy_pipeline/artifacts/strategy_engineering.md)
