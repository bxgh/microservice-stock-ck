# EPIC-019 开发结项与进度报告 (Geopolitical Defense Strategy)

**报告日期**：2026-03-11  
**报告人**：Antigravity Agent (A股策略开发助手)  
**涉及微服务**：`quant-strategy`, `get-stockdata`

## 1. 总体进度 (Overall Progress)
截至本报告日期，**EPIC-019 地缘政治防御选股策略** 已全线打通并交付。系统现已具备在国际冲突与局部战争等极端避险情绪爆发时，自动诊断市场情景（闪电战、僵持期、持久战），并极速穿透全量 A 股完成抗逆性评分的能力。

## 2. 完成的 Story 列表 (Completed Stories)
1. **[Story 19.1] 跨类资产(原油期货) 数据源整合**：
   - 在 `mootdx-source` 底层完成了 `DATA_TYPE_FUTURES_KLINE_DAILY` 扩展。
   - 实现并验证了 WTI(CL) 及 Brent(OIL) 的历史数据回溯及增量入库机制。
2. **[Story 19.2] 策略级宏观情景探测大脑 (`ScenarioDetector`)**：
   - 根据原油的绝对涨跌幅度、价格偏离均线百分比，结合战争持续时间动态划分 `SCENARIO_A/B/C`。
3. **[Story 19.3] 动态防御性资金/行业偏好加点 (`GeopoliticalScoringService`)**：
   - 提取申万/同花顺中如“黄金”、“国防军工”、“油气开采”、“农业安全”的题材溢价，按宏观情景注入差异化得分系数。
4. **[Story 19.4] K线级别个股生存力评分 (`DefenseFactorService`)**：
   - 基于本地 `ClickHouseKLineDAO` 对截面最大回撤幅度、区间相对基准超额收益、缩量流度等方面产出量化分级指标。
5. **[Story 19.5] 自动化调仓机制落地 (`CandidatePoolService`)**：
   - 新增 `refresh_geopolitical_pool` 专用工作流，采取了基于 `Semaphore` 的并发保护以及 Clickhouse 客户端多线程并发加锁措施，成功实现在极短时间内扫完 5700+ A股并产出最终 Top 20 强避险推荐库。

## 3. 技术优化与风险解决 (Technical Resolutions)
- **依赖注入与脱机模式补丁 (Singleton Patching)**
  因 `gRPC` 跨服务在高并发请求大量个股因子数据时存在超时连接与网络异常，我们在脚本执行环境利用动态命名空间单例替换（依赖注入）的方式，无缝引入纯离线 K线读取（直接连 `ClickHouse` 本地池），避免了业务核心代码污染并保证了并发的成功率。
- **并发与锁机制防护 (Thread/Asyncio Safety)**
  修复了 `clickhouse-driver` 在执行 `run_in_executor` 时可能引发的 `Simultaneous queries` 同步冲突错误。

## 4. 下一步计划 (Next Steps)
该 Epic 各项功能经 `/code_quality_check` 测试及 `mypy` 检验，已扫清影响业务逻辑的代码级技术债。
由于策略参数受人为定义较为灵活（如具体冲突起始日、各周期权重），建议：
1. 观察生产环境下 `CandidateStock` 中 `pool_type='geopolitical'` 表每天更新的选股数据流是否稳定落盘。
2. 着手实盘资金验证前的轻量化回测工作流 (Backtest Framework Support)。
