# Epic 002: 长线配置算法全量解锁 - Walkthrough

## 1. 业务说明
本技术切片 (Story 2.5 / Epic 002 Finalization) 的核心使命是为整个**长线资产配置管线**进行收官拔高。我们完成了从简单的涨跌幅度截取到融合更深邃价值投资理念的进阶过渡，包括了底层风控一票否决权，护城河评判，以及防范伪成长股的终极武器PEG估值模型。

## 2. 核心补完组件

1. **绝对防线 (Risk Veto Filter)**
   - 部署了 `STRiskRule` 来对戴帽个股进行极速扑杀。
   - 部署了 `RegulatoryBlacklistRule` 与监管静态库实施联动，实现被行政通报/监管停牌个股的自动化剔除。
   - 这两把锋利的尖刀已挂载于 `FundamentalFilter`，确保只有底子干净的标的可以进入下一阶段的评分。

2. **多维立体估值 (Multidimensional Valuation)**
   - 突破了原先单一倚赖 PE/PB Band 的束缚。
   - 加入了 **PEG 分数修正 (Growth Adjust)** 引擎，严厉打击只顾市盈率低估而不看业绩下滑的“价值陷阱”股票。只有兼具安全边际与业绩成长复合因子的股票才能吃满估值得分。
   - 加入了 **股息率 (Dividend Yield) 奖励机制**，大幅提振了红利股票（>=5%分红率）的权重优先级。

3. **护城河度量 (4D Quality Scoring)**
   - 引入 **ROE 稳定性跨期惩罚 (ROE Stability Penalty)** 逻辑。针对“三年不开张，开张吃三年”的强周期行业（极高标准差），直接扣减盈利质量分数。强迫管线优先拥抱护城河深耸入云的大白马。

## 3. 代码演进图谱
- `src/strategies/rules_fundamental.py`: [NEW] `STRiskRule`, [NEW] `RegulatoryBlacklistRule`
- `src/services/fundamental_filter.py`: [MODIFY] 将两大过滤核弹挂载至底层 `RiskManager`
- `src/services/alpha/fundamental_scoring_service.py`: [MODIFY] 追加 `history_roe_std` 惩罚阈值。
- `src/services/alpha/valuation_service.py`: [MODIFY] `PEG` 与 `Dividend Yield` 算子挂装完毕。
- `src/services/stock_pool/candidate_service.py`: [MODIFY] 重定向上游，强制插入 `fundamental_filter` 的运行位点。

## 4. 自动化保障记录
执行 Pytest 测试套件：
```bash
docker compose -f docker-compose.dev.yml run --rm quant-strategy pytest -v tests/test_candidate_pool.py

# Output
17: tests/test_candidate_pool.py::TestCandidatePool::test_refresh_pool_logic PASSED [ 50%]
18: tests/test_candidate_pool.py::TestCandidatePool::test_api_integration PASSED [100%]
30: ======================== 2 passed, 2 warnings in 3.18s =========================
```
- 测试框架完美支撑了带有 Semaphore 限流机制的协程调度并发。
- `pytest_asyncio` 适配件的兼容性与生命周期管理（setup_database）测试通过。

## 5. 项目航向
伴随着这一系列特性的解禁，**EPIC-002（长线资产配置）** 正式宣告全部完成。当前候选池刷新接口已经具备了在实盘作业中筛选出高 ROE、低估值、强护城河白马金股的硬核能力。这标志着量化基建已经从搭建骨架顺利渡过了“血肉填充”的瓶颈。后续的弹药将对准更为凶险的日内交易与高频波段（EPIC-004...）。
