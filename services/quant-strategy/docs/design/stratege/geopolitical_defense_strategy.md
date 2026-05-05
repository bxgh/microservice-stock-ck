# 地缘政治防御选股策略 (Geopolitical Defense Strategy)

## 1. 策略概述
**策略类型**：事件驱动 / 宏观防御避险
**适用域**：A股全市场
**主要目标**：在地缘政治冲突、局部战争等极端风险爆发期间，通过结构化的防御性资产配置，最小化总资产组合波动并博取脉冲性超额收益。

## 2. 核心架构与模块

### 2.1 情景感知引擎 (`ScenarioDetector`)
依赖于外盘期货（如 WTI原油 `CL` / Brent原油 `OIL`）及 A股大盘指数的历史走势与波动率，动态判定当前宏观风险级别。
- **Scenario A (闪电战/爆发初期)**：持续时间 $\le$ 14 天。大宗商品飙升，避险情绪极高。
- **Scenario B (中度冲突/僵持期)**：14天 < 持续时间 $\le$ 90 天。情绪趋缓，市场聚焦局部受益板块（如供应链断裂替代）。
- **Scenario C (持久战)**：持续时间 > 90天。极度看重上市公司本身的防御性和高股息（基本面支撑）。

### 2.2 防御因子提取 (`DefenseFactorService`)
通过本地 ClickHouse 截面数据（`ClickHouseKLineDAO` 支持高并发与连接重试），计算各股票的防御属性指标：
1. **抗跌超额收益率 (Excess Return)**：相较于大盘基准，在风险事件区间内的相对收益水平。
2. **风险期最大回撤 (Max Drawdown)**：区间内最大回落幅度。
3. **资金流动性特征 (Volume Ratio)**：区间缩量/放量比，防范流动性衰竭导致的踩踏风险。

### 2.3 避险加成引擎 (`GeopoliticalScoringService`)
基于行业与概念分类（如申万行业分类或自定义同花顺概念），自动检测个股身上的“避险标签”池：
- **一级防御/战争直接受益**：黄金、军事防务/航天军工、油气开采与炼化。
- **二级防御/资源保障**：公用事业（电力网络）、中药、农业/粮食安全。

### 2.4 终期评定引擎 (`GeopoliticalScoringEngine`)
综合以上全部指标，分别在 0-100 区间做 Min-Max Normalization：
* `Final_Score = 0.3 * ExcessReturn + 0.2 * MaxDrawdown + 0.1 * VolRatio + 0.2 * Bonus + 0.2 * BaseAlpha`

*(注：不同 Scenario 的权重分布会有所偏转。例如在 Scenario A 下，Bonus 的权重会被放大)*

## 3. 工程实施落点
1. **统一数据源接入**：通过 `mootdx-source` 代理层收集并在 ClickHouse 的 `futures_kline_daily` 存档大宗商品数据。
2. **多例注入规避网络抖动**：主节点评测在 `CandidatePoolService.refresh_geopolitical_pool` 执行，强制使用本地 ClickHouse 直连（Offline 模式），辅以 `Semaphore(50)` 及 `asyncio.Lock()`，能在 5。分钟内穿透 5770 支 A 股进行脱机运算并输出池类 Top 20 调仓推荐。

## 4. 风险控制要求
- 单票最大回撤惩罚：若标的发生过 >= -15% 的连续跌停/极速单日杀跌，即使总评分高也需从 Top Pool 中剥离。
- 参数定期标定：需随着事件推移每日修正距离原初爆发点的 `Event_T0` 时间戳参数。
