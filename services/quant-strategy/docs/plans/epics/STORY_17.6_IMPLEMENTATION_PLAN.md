# Story Implementation Plan

**Story ID**: 17.6  
**Story Name**: 另类数据信号注入通用选股全流程  
**开始日期**: 2026-02-28  
**预期完成**: 2026-02-28  
**负责人**: AI Assistant

---

## 📋 Story概述

### 目标
打通“另类数据策略”最关键的一环：将产生出来的诸如 `HOT` 等开源社区热度评级，自动翻译成它在 A 股映射的同花顺所属概念板块（如 "人工智能", "算力" 等），在现有的预选股票池加分漏斗中拔高校准后的策略最终评分。

### 验收标准
- [ ] 新建概念关系映射器。允许把如 `deepseek` 的技术打星直接映射为大 A 当中的某个 `概念代码/名称`。
- [ ] 修改每日选股票池逻辑（或类似于 `CandidatePoolService`，依据代码仓库现状）。使用 `AltDataDAO` 取出今日最新的有效信号表。
- [ ] 获取受影响板块成分股，给予策略中配置的信号权重红利。
- [ ] 加入 `try-except` 或 `CircuitBreaker` 异常隔离结构：若 ClickHouse `altdata` 库掉线或解析出现 Bug，主策略选股降级但不能终止服务！

### 依赖关系
- **依赖Story**: Story 17.5 (计算引擎完结)。
- **外部依赖**: 系统的 `mootdx-source` 概念成分股拉取，原项目的评分逻辑机制（EPIC-005 或框架 4.0 的选股管线）。

---

## 🎯 需求分析

### 功能需求
1. **Label ↔ Concept 映射字典或配置**:
   - `deepseek` / `vllm` / `huggingface` -> \`人工智能\` | \`AIGC概念\` | \`算力租赁\` 等对应。
2. **权重加分**:
   - 原分数比如 80分，若成分股享有 `HOT` 的标签：最终分数为 `80 * 1.10 = 88` 或 `80 + 10`。
   - EXTREME 加成：1.15
   - WARM 加成：1.05
   - NEUTRAL：无加成

---

## 🏗️ 技术设计

### 核心组件

#### 组件1: `src/config/altdata_mapping.yml` 或 `src/config/mapping.py`
**职责**: 定义技术标签到国内板块名称的硬绑定。

#### 组件2: `src/services/candidate_pool.py` (依据现有目录存在情况，或是等价评分扫描服务)
**职责**: 修改原有的股票筛选打分 `evaluate` 循环。在这个阶段里，异步插入一步查询 `AltDataDAO` 获取最新有效（`signal_level != NEUTRAL`）名单的动作。而后交叉比对进行加成。

---

## 📁 文件变更

### 新增文件
- [ ] `services/quant-strategy/src/config/altdata_mapping.py` （采用 Python 字典便于导入和管理变更）

### 修改文件
- [ ] `services/quant-strategy/src/dao/industry.py` (确认是否自带成分股查询，视查勘情况定)
- [ ] 选股核心评分类/服务：(我们将在规划阶段下半程探查并确定为 `services/scanner/` 或 `services/candidate_pool.py`)。

---

## 🔄 实现计划

### Phase 1: 概念股关联探索
- [ ] 查阅现有 `quant-strategy/src/dao/industry.py` 或者 `quant-strategy/src/services/` 判断如何在引擎内查询属于某一个板块的全部代码，然后记录这些方法的输入规范。

### Phase 2: 修改扫描主循环
- [ ] 给选股器赋予获取最后一次成功生态信号快照的功能。
- [ ] 根据映射字典，得到所有 `WARM` 以上被“激活”板块的全部成分股。
- [ ] 将加分写入最后报告中例如 `details["生态动量增幅"]` 中以便后期归因分析。

### Phase 3: 断电容灾与降级
- [ ] 封装拉取 `alt_signals` 到安全执行包裹里，发生 `ReadTimeout` 不干扰大局。

---

## 🚨 风险与缓解

| 风险 | 影响 | 可能性 | 缓解措施 |
|------|------|--------|----------|
| 找不到对应的 A 股概念匹配 | 中等 | 中 | 首先利用已知的泛泛概念（如 "AIGC"）做关联测试，不追求全维度。 |

---
