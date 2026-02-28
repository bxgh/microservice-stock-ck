# Story 004.03 - 日内动量与隔夜套利 (IntradayEngine)

## 📌 背景
随着前序工作（`TickClusterStrategy`）将盘后的深海全市场大数据矩阵运算理清，Epic 004 来到了最敏捷刺激的环节：**利用日内分钟数据切片，抢夺最凶狠的突破收益。**
这是由于 A 股市场 T+1 和特殊的集合竞价机制：最核心的 alpha（据研究占比>90%）全发生在前一晚的隔夜跳空和开盘的最早 30 分钟内。此模块旨在拦截这些瞬时的“不理性”定价。

---

## 🏗️ 核心成就

### 1. 动量跳空检测 (Analyze Overnight Gap)
为策略注入了极度前瞻的防爆逻辑。
- 我们使用 `gap = (今日开盘价 - 昨日收盘价) / 昨日收盘价` 给出了情绪热度的测量值。
- 但大涨大跌不能一刀切！我们用 **前 30 分钟成交量 / 前 20 日同时间点均量 (`VolumeRatio`)** 为其“测谎”。倘若股票今天高开 3%，但并没有巨量配合 (`< 1.5倍`)，模型将直接抛出 `GAP_FADE` 并带上 `SHORT` 方向标签，拒绝在高位接盘主力诱多。反之巨量突破则会拉满火力输出 `GAP_FOLLOW`。

### 2. 星际传导链雷达 (Analyze Momentum Transmission)
最巧妙的同集群内跨股套利：
利用昨日 `Leiden` 计算出来的领头羊身份 (Leader)。如果在 9:30 - 10:00，系统侦测到龙头股票爆拉超过 3%，但同属一个行业圈（同 Cluster ID）的小弟还未觉醒上涨 (< 1%)：
引擎会向其发去 `MOMENTUM_LAG` 并直接估出可能有的传导价差分数。这种跟风追捕极具交易确定性！

### 3. 日内数据模型 (`IntradaySignal`)
新撰写了附带微观特征属性的数据报文实体 `IntradaySignal`。里面包含了诸如 `gap_percent` / `volume_ratio` 等只有毫秒微积分才在乎的属性。独立与收盘静态的 `Signal` 接口。并在 `TickClusterStrategy.generate_intraday_signals` 形成了日内大门向外部回测调度开放。

---

## 👉 查看文件
- **日内分析模型层**: [models.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/analysis/intraday/models.py)
- **动能跳空测算逻辑**: [momentum_analyzer.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/analysis/intraday/momentum_analyzer.py)
- **挂载入策略外壳**: [tick_cluster_strategy.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/strategies/tick_cluster_strategy.py)
- **自动化防漏金测试**: [test_intraday_momentum_analyzer.py](file:///home/bxgh/microservice-stock/services/quant-strategy/tests/analysis/test_intraday_momentum_analyzer.py)

> 🎉 **这也标志着跨越四大周期的 EPIC-004 风控与增强体系 全部开发完毕并顺利结项！**
