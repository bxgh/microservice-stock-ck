# 项目知识库建设——待选主题清单

本列表由系统扫描全量文档后，依据架构影响度、业务关键度与信息密度综合评估生成。

---

## 一、核心架构类 (P0 - 强烈建议建库)
这些内容定义了系统的骨干逻辑，对后续开发与故障排查至关重要。

1.  **[ ] 微服务分层与通信规范 (RPC/Nacos)**
    - *来源*: `docs/plans/microservice_refactoring/ADR-001-data-source-microservices.md`
    - *价值*: 规定了服务间调用的边界与标准，是系统稳定性的基石。
2.  **[ ] 数据治理门禁闭环 (Gate 1/2/3)**
    - *来源*: `services/task-orchestrator/docs/data_gates/`
    - *价值*: 详述了系统的三级防线与自动修复逻辑，是数据准确性的保障。
3.  **[ ] 分布式指令驱动架构 (V3.0/V4.0)**
    - *来源*: `services/task-orchestrator/docs/task_scheduling/`
    - *价值*: 解析了系统如何跨机器调度任务，是理解大规模背景作业的关键。

---

## 二、量化策略类 (P1 - 业务核心)
涵盖分笔数据的特征提取与策略实现细节。

4.  **[ ] 量化策略分析管线 (Tick Analysis Pipeline)**
    - *来源*: `services/quant-strategy/docs/design/分笔数据/`
    - *价值*: 记录了特征库、DTW 相似度、聚类引擎的实现逻辑，是策略开发的核心。
5.  **[ ] 宏观因子与数据指标定义**
    - *来源*: `services/quant-strategy/docs/reports/EPIC_READINESS_ASSESSMENT_20260205.md`
    - *价值*: 明确了 OFI、Smart Money 等关键因子的计算口径。

---

## 三、基础设施与运维类 (P2 - 稳定性辅助)
记录了网络优化、数据库演进及运维经验。

6.  **[ ] A股行情源连接与多网卡优化 (TDX/Triple-NIC)**
    - *来源*: `docs/operations/SERVER_58_TRIPLE_NIC_DEPLOYMENT.md`, `docs/operations/SERVER_58_MOOTDX_API_ISSUE_20260108.md`
    - *价值*: 核心技术突破，解决了分笔采集的物理瓶颈。
7.  **[ ] ClickHouse 分布式架构与扩容实录**
    - *来源*: `docs/operations/CLICKHOUSE_3NODE_EXPANSION.md`, `infrastructure/clickhouse/QUICK_REFERENCE.md`
    - *价值*: 记录了从单点到三节点集群的扩容经验与性能调优。
8.  **[ ] 分布式集群部署与代码同步手册**
    - *来源*: `docs/operations/FULL_DEPLOYMENT_GUIDE_20260120.md`, `docs/operations/CODE_SYNC_STRATEGY.md`
    - *价值*: 运维标准化文档，对多节点维护至关重要。

---

## 五、微服务深度专项 (P4 - 技术专题)
针对特定微服务的高级技术说明。

13. **[ ] 分笔数据采集并发与策略深度指南**
    - *来源*: `services/gsd-worker/docs/分笔数据采集策略与并发指南.md`
    - *价值*: 详细解析了多线程/异步采集时的流量控制、重试退避及性能瓶颈优化。
14. **[ ] 龙虎榜数据扩展 (Dragon-Tiger Extension)**
    - *来源*: `services/mootdx-source/docs/DRAGON_TIGER_EXTENSION_DEMO.md`
    - *价值*: 记录了如何接入异构的特色行情数据（龙虎榜），是数据源扩展的典型案例。
15. **[ ] 策略开发与代码演进指南**
    - *来源*: `services/quant-strategy/docs/antigravity_code_development_guide.md`
    - *价值*: 针对量化策略编写的专项工程规范。

## 六、策略探索与方法论 (P5 - 知识储备)
16. **[ ] 分笔数据分析框架与苏格拉底式自查点**
    - *来源*: `docs/brainstorming/analysis-strategy-framework.md`, `docs/brainstorming/socratic-tick-analysis-checklist.md`
    - *价值*: 记录了策略设计的思维模型与质量自查标准。
17. **[ ] 数据源插件开发规范 (AkShare/Mootdx Source)**
    - *来源*: `docs/development/akshare-source.md`, `docs/development/mootdx-source-extension-guide.md`
    - *价值*: 异构数据源接入的标准流程。

---

**请在回复中指定您希望优先建库的主题序号（例如：1, 6, 9），我将立即为您执行知识蒸馏。**

---

**请在回复中指定您希望优先建库的主题序号（例如：1, 3, 5），我将立即为您执行知识蒸馏。**
