# Epic: [E100] Agent 实施约束与技能体系优化

> 本文档记录对 `AGENTS.md` 的审计结果及后续实施体系的改造规划。旨在通过模块化与自动化手段，降低 Agent 的信息熵，确保 A 股盘后系统实施的高可靠性。

## E100-S1: 实施现状多维审计 (Analysis)

### 任务
- [x] 1. 从设计、开发、归档、部署四个维度进行现状评估
- [x] 2. 识别各维度的核心价值与潜在风险

### 验收标准 (AC)
- **Given**: `AGENTS.md` 包含全量实施约束。
- **When**: 执行多维深度分析。
- **Then**: 
    - **设计维度**: 确认 Epic-Story 结构的稳定性，指出业务口径膨胀风险。
    - **开发维度**: 确认“单位陷阱”与“软删除过滤”的核心价值，指出人工记忆的不可靠性。
    - **归档维度**: 确认“真源验证”的严谨性，指出文档回填的工作量负担。
    - **部署维度**: 确认 41 节点与 Gost 隧道的强制性。

---

## E100-S2: 规则冗余与冲突清理 (Audit)

### 任务
- [x] 1. 对比 `AGENTS.md` 与 `python-coding-standards.md` 的重叠项
- [x] 2. 对比 `AGENTS.md` 与 `quant-strategy-standards.md` 的口径差异

### 验收标准 (AC)
- **Given**: 存在多份工程标准文档。
- **When**: 进行全量内容审计。
- **Then**: 
    - **冗余识别**: 识别出并发安全 (`asyncio.Lock`)、熔断重试 (`CircuitBreaker`)、时区要求 (`Asia/Shanghai`) 在多处重复定义。
    - **冲突识别**: 识别出 `amount` 单位（元 vs 千元）在量化策略层与采集层可能存在的口径失准。
    - **结论**: 建议将底层技术标准收敛至 `python-coding-standards.md`，`AGENTS.md` 仅保留 A 股领域知识。

---

## E100-S3: 体系模块化与自动化改造方案 (Design)

### 任务
- [x] 1. 设计基于角色的虚拟 Agent 约束分片 (Role-based Rules)
- [x] 2. 规划自动化辅助技能 (Skills) 工具链

### 验收标准 (AC)
- **Given**: Agent 在处理长文档时存在信息遗忘风险。
- **When**: 提出改造架构建议。
- **Then**: 
    - **角色分片**: 定义 [DB Auditor] (盯单位与命名)、[Workflow Guard] (盯流程与证据链)、[Infra Specialist] (盯部署与代理)。
    - **技能规划**: 
        - `skill:data-validator`: 自动校验 SQL 单位与 `TABLES_INDEX.md` 是否一致。
        - `skill:walkthrough-generator`: 自动从日志与数据库查验结果中提取证据链。
        - `skill:schema-enforcer`: 自动检查 DDL 是否符合“尾部三件套”规范。
---

## 实施结果总结 (Final Summary)

本 Epic [E100] 已于 2026-05-09 完成闭环。

### 1. 规则体系重构
- **解耦**: 实现了技术底座 (`python-coding-standards.md`) 与业务/基建主控 (`AGENTS.md`) 的物理分离。
- **对齐**: 修复了量化策略层与采集层在 `amount` 单位（元）与字段命名 (`ts_code`) 上的口径冲突。

### 2. 角色化审计体系
- **ROLES.md**: 建立了虚拟 Agent 角色模型，将 19KB 的 `AGENTS.md` 约束分片为：
    - **[DB Auditor]**: 专项盯防 SQL 过滤、命名及单位换算。
    - **[Workflow Guard]**: 专项盯防流程合规、存证完整性及准入检查。
    - **[Infra Specialist]**: 专项盯防节点限制、网络代理及流量红线。

### 3. 自动化演进路径
- **SKILLS_ROADMAP.md**: 规划了从“人工记忆”转向“工具驱动”的技术路线，优先聚焦存证自动生成与数据契约校验。

## 角色激活指南 (Usage Guide)

为了确保本 Epic 的改造落地，Agent 在后续实施中必须遵循以下机制：

### 1. 计划阶段显式声明
在每个 Story 的 `implementation_plan.md` 中，必须在“架构溯源”部分注明激活的角色。
> 示例：**激活角色**: [DB Auditor], [Workflow Guard]

### 2. 验收阶段角色自查
在 `walkthrough.md` 中，Agent 必须以激活角色的身份给出最终审计结论。
> 示例："[DB Auditor] 已通过 `skill:data-validator` (规划中) 手工对比确认，所有指标单位符合 AGENTS.md 规范。"

---
**Status**: ✅ COMPLETED (Phase 1)
**Author**: Antigravity
