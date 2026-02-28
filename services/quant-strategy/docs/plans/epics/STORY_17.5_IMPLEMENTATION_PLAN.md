# Story Implementation Plan

**Story ID**: 17.5  
**Story Name**: 生态信号计算引擎 (quant-strategy)  
**开始日期**: 2026-02-28  
**预期完成**: 2026-02-28  
**负责人**: AI Assistant

---

## 📋 Story概述

### 目标
在 `quant-strategy` 微服务中建立数据通道和策略类，用于定期拉取 `altdata.github_repo_metrics` 中的数据，经过标准化与 Z-Score 计算，提取出复合的生态信号指标（动量、响应速度、增量），最终输出信号强弱分类（NEUTRAL, WARM, HOT, EXTREME），并落盘回 `altdata.ecosystem_signals` 中。

### 验收标准
- [ ] 在 `src/dao/altdata.py` 中实现 `AltDataDAO`，用于基于标签 (label) 和时间区间查询采集的原始 GitHub 特征数据，并提供将聚合信号插回 ClickHouse 的能力。
- [ ] 在 `src/strategies/eco_signal_strategy.py` 中实现 `EcoSignalStrategy` (继承自 `BaseStrategy` 或独立计算类)，利用 Pandas 和 Numpy 向量化运算实现提纯规则。
- [ ] 生成包含 `composite_z_score`, `dominant_factor`, `signal_level` 等字段的结果数据。
- [ ] 为计算引擎增加基于 mock 数据的单元测试。

### 依赖关系
- **依赖Story**: Story 17.1-17.4 (上游数据产出已就绪)。

---

## 🎯 需求分析

### 功能需求
1. **多指标归一与聚类**:
   - `eco_momentum`: 由 `pr_merged_acceleration` + `commit_count_7d` 组成。
   - `eco_responsiveness`: 由 `issue_close_median_hours` 的倒数组成（耗时越短越快）。
   - `eco_growth`: 由 `star_delta_7d` + `contributor_count_30d` 组成。
2. **滚动窗口基础 Z-Score**: 使用最新一次拉取与过去 30 天数据的均值与标准差对比，生成评分。
3. **阈值映射**: 
   - `Z < 1` -> NEUTRAL
   - `1 <= Z < 2` -> WARM
   - `2 <= Z < 3` -> HOT
   - `Z >= 3` -> EXTREME

---

## 🏗️ 技术设计

### 核心组件

#### 组件1: `src/dao/altdata.py` - `AltDataDAO`
**职责**: 与 ClickHouse 的交互，由于 `quant-strategy` 已有成熟数据库连接体系（参见内部库），复用项目的 ClickHouse Client 并编写相应的 Select/Insert SQL。

#### 组件2: `src/strategies/eco_signal_strategy.py` - `EcoSignalStrategy`
**职责**: 计算核心。接收一个被 `AltDataDAO` 抓取回来的 `pd.DataFrame`，执行 Pandas 向量化处理，避免使用 Python Loop。输出包含结果行的 Signal DataFrame。

---

## 📁 文件变更

### 新增文件
- [ ] `services/quant-strategy/src/dao/altdata.py`
- [ ] `services/quant-strategy/src/strategies/eco_signal_strategy.py`
- [ ] `services/quant-strategy/tests/strategies/test_eco_signal.py` (单元测试)

### 修改文件
- 无重大基础组件修改，主要为纯粹的能力拓增。

---

## 🔄 实现计划

### Phase 1: DAO 开发
- [ ] 探明项目内现有的 Db 客户端，在 `quant-strategy/src/dao/` 创建针对 `altdata` 指定数据库读写的方法。

### Phase 2: 分析策略与集成
- [ ] 利用 Pandas 将 6 大特征合并为 3 大高维特征。
- [ ] 根据 Z-Score 处理为分级信号并附带当时提取的信号生成时间 `signal_time`。
- [ ] 编写 PyTest 测试函数，保证各种信号特征能够被正确映射到诸如 `HOT` / `EXTREME` 类别。

---

## 🧪 测试策略
- **单元测试**: 使用 Pytest 对 `EcoSignalStrategy.generate()` 方法编写大量含各类拐点的数据 DataFrame，例如让历史均值极低而今日飙升以确认产生 `EXTREME` 信号。 
- **集成测试**: 尝试直连真实 ClickHouse 进行查询和插入一次信号的往返操作验证。

---
