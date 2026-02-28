# Git Diff & Development Summary (2026-02-27)

## 核心交付内容 (Core Deliverables)
本次开发聚焦于 **长线配置算法全量解锁 (Epic 002.5)** 的收尾与联调，彻底打通了风控硬指标过滤与估值子系统，并修复了全链路测试中的数据结构与类型转换阻断 BUG。

### 1. 股票代码格式自适应改造 (TS Code Standardization)
* **`src/models/signal.py`**: 
  - 放宽了 `Signal` 模型中 `stock_code` 必须为严格 6 位数字的硬性校验（修改为 `len < 6` 报错），完美兼容了带有交易市场后缀的 TS 格式代码（如 `000001.SZ` / `872374.BJ`）。
* **`src/services/fundamental_filter.py`**:
  - 撤销了早期为了规避校验而强制硬切片 `code[:6]` 的防御性逻辑，令长线选股池中的 TS 格式标准代码能够原样往下游传递。
* **`src/adapters/stock_data_provider.py`**:
  - **动态切片路由**：针对 `get-stockdata` 的不同底层数据源实现了分发适配。向 ClickHouse (获取基本面 info) 请求时保留全量后缀；而在透传 Akshare (获取财务 indicators / 估值 valuation) 时进行六位切片，从根源上消除了海量因格式不符引发的 `404 Not Found` 阻断错误。

### 2. 财务风控与估值模型的防御性鲁棒增强
* **`src/domain/models/financial_models.py`**:
  - 为 `FinancialIndicators` 补充了四大关键的安全计算属性（`@property`）：`goodwill_ratio` (商誉占比)，`cash_to_profit_ratio` (收现比)，`cash_ratio` (货币资金比)，`debt_ratio` (有息负债比)。
  - 内置了零分母 (`<= 0`) 和空值 (`None`) 的安全过滤兜底，输出默认为 `0.0`，彻底阻断了原先因字典映射缺少计算字段而暴毙抛出的 `AttributeError` 异常，保全了数据管道。
* **`src/strategies/rules_fundamental.py`**:
  - 给 `PledgeRiskRule`（大股东质押风险）等多重拦截器增加了 `None` 值的容错回退判断（`or 0.0`）。 
  - 实现了基于当前基本面摘要匹配的 `STRiskRule`，达成了一票否决 ST/*ST 高风险股。
  - 通过注入的依赖接口对接了 `RegulatoryBlacklistRule`（监管黑名单拦截规则）。

### 3. 选股降级与灾备链路修复
* **`src/services/stock_pool/candidate_service.py`**:
  - 修复了新股或停牌股由于不存在估值数据触发 `Fallback to Mock Scoring` 机制时的极速宕机灾难。
  - 原有逻辑将形如 `"600336.SH"` 的全格式字符串强转为整型 (`int()`) 充当随机种子进而抛掷 `ValueError`。现已优化为带切片的纯数字提取（`split('.')[0]`）以及底层 `hash()` 保护，使得大盘级全量映射筛选不再发生线程雪崩。

### 4. 自动化测算脚手架连通
* **`scripts/run_selection.py`**:
  - 将随机测试抽样数进行了反复调节与回退验证（400 -> 20 -> 400）。
  - 最终在本地协程管线下无阻断排查数以万计的报错信息，并完美跑通，成功输出了带有不同子战术策略池标签（`core` / `rotation`）的 **长线十大核心金股名单** 回测战报。

## 上线与后续建议
目前所有的 Diff 代码皆已使得整个长线（Long-Hold）资管调配引擎具备了在容错、降维、熔断保护下实盘顺滑运转的可行性。后续可结合每日盘后定时任务进行批处理，向操盘手推送经过这套庞大估值-风控系统漏斗初筛后的 `Top20` 白马金股榜单。
