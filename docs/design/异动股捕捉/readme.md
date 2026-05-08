# 异动捕捉模块 · 设计交付文档 (v1 极简版)

| 项 | 内容 |
|---|---|
| **当前版本** | v1.0 (极简版) |
| **设计冻结** | 2026-05-07 |
| **核心目标** | 建立评估体系, 识别极端市况, 极简分类打标 |
| **状态** | **设计已锁定, 准备实施** |

---

## 1. 简介

本模块旨在为 L8 异动系统建立**闭环评估能力**。通过先建设回测子系统, 我们能够用客观数据指导后续的评分算法优化, 避免盲目调参。同时引入极端市况下的策略切换机制(D 视图), 解决评分系统在普涨/普跌日失效的问题。

---

## 2. 文档索引 (v1 极简版)

1.  **[00_OVERVIEW 设计全景](file:///home/bxgh/microservice-stock/docs/design/异动股捕捉/00_OVERVIEW.md)**: 背景、设计哲学、目标范围、里程碑及风险评估。
2.  **[E1 主表增量改造](file:///home/bxgh/microservice-stock/docs/design/异动股捕捉/E1_SCHEMA_REFORM.md)**: `ads_l8_unified_signal` 字段扩展与版本化权重配置。
3.  **[E2 评估子系统](file:///home/bxgh/microservice-stock/docs/design/异动股捕捉/E2_EVALUATION_SUBSYSTEM.md)**: 标注表设计、历史回填、月度回测与自动化报告。
4.  **[E3 异动分类逻辑](file:///home/bxgh/microservice-stock/docs/design/异动股捕捉/E3_CLASSIFICATION_LOGIC.md)**: C1-C4 单标签分类规则与评分溯源 JSON 存储。
5.  **[E4 极端市况与 D 视图](file:///home/bxgh/microservice-stock/docs/design/异动股捕捉/E4_EXTREME_MARKET_GATING.md)**: 普涨/普跌识别逻辑、推送切换及市场全景简报。
6.  **[E5 & E6 集成与文档](file:///home/bxgh/microservice-stock/docs/design/异动股捕捉/E5_E6_INTEGRATION_AND_DOCS.md)**: 管线任务增补与全局索引文档同步。

---

## 3. 历史版本
- **[Legacy v1.1 (完整版)](file:///home/bxgh/microservice-stock/docs/design/异动股捕捉/legacy_v1.1/)**: 包含 22 个细分标签的复杂方案(因过度工程暂缓实施)。

---

## 4. 核心共识 (极简版)
- **评估先行**: 没有回测数据的评分优化都是玄学。
- **单标签简化**: 第一阶段不搞多标签重叠, 命中即停。
- **极端市况兜底**: 涨跌停 > 100 家时, 评分失效, 改看全场梯队。
