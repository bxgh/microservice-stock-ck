# Story Walkthrough: 生态信号生成引擎 (quant-strategy)

**Story ID**: 17.5  
**完成日期**: 2026-02-28  
**开发者**: AI Assistant  
**验证状态**: ✅ 通过

---

## 📊 Story概述

### 实现目标
开发处于 `quant-strategy` 微服务内部的数据中控以及计算中台（`AltDataDAO` 及 `EcoSignalStrategy`），负责调取在 Phase 1 (17.1-17.4) 保存至数据库中的非结构化原始数据，把开源热度转化为 4 种强弱分级的资金引导信号。

### 关键成果
- ✅ 开发了连接专属生态数据库的 `AltDataDAO`，无缝返回 `Pandas.DataFrame` 以支持高速科学计算。
- ✅ 实现了高维纯向量计算类 `EcoSignalStrategy`，完全抛弃缓慢的 `Python for loop` 迭代过程。
- ✅ 依照 30 日移动均值的 `Z-Score` 将技术生态划定为 NEUTRAL / WARM / HOT / EXTREME 阈值。
- ✅ 配备完善、覆盖噪音注入与单项/多维度突增激变的 `PyTest` 断言环境，所有逻辑用例通过。
- ✅ 构建了 `src/jobs/altdata_signal_job.py` 日终管道，供任意外部定时器驱动以全量更新数据库数据状态。

---

## 🏗️ 架构与设计

### 系统架构
```mermaid
graph TD
    Job[altdata_signal_job (每日触发)] --> DAO[AltDataDAO]
    DAO -->|"1. 提数 get_raw_metrics (ClickHouse)"| DB[(CH: github_repo_metrics)]
    
    Job --> Strat[EcoSignalStrategy]
    Strat -->|"2. Numpy/Pandas 算例求出信号矩阵"| Job
    
    Job --> DAO
    DAO -->|"3. 写回分级 insert_signals"| DB_Sig[(CH: ecosystem_signals)]
```

### 核心组件
1. **`src/dao/altdata.py: AltDataDAO`** 
    使用 `clickhouse_connect` 的 DataFrame I/O 功能，无缝打通时序与 AI。
2. **`src/strategies/eco_signal_strategy.py: EcoSignalStrategy`** 
    聚合运算。具备三个分项分数: `momentum`, `responsiveness`, `growth`；及合成加权分数 `composite_z_score` 和主力诱导因素定位。

---

## 💻 代码实现

### 核心代码片段

#### [功能1]: 时间序列的防除 0 平滑映射
```python
# Responsiveness: issue 响应极值。由于数值越低响应越快代表活性越强，使用负倒数进行同质化：耗时越小值越大
# 为避免除以 0 以及平滑数据，采用 24 / (x + 1) -> 即 1 天为基准的活跃比
df["eco_responsiveness"] = 24.0 / (df["issue_close_median_hours"] + 1.0)
```

**设计亮点**:
- 有效遏制了社区极端小样本导致的 `除零错误` 并将该原本逆向的参数统一归还为了 `正向因子`（数值越大=景气度越高）。

#### [功能2]: 防止方差收缩为 0 的异常判断
```python
# 使用 numpy where 安全处理标准差等于0的情况 (除以0得到NaN)
df[z_col] = np.where(std > 0, (df[col] - mean) / std, 0.0)
```

**设计亮点**:
- 初期某些库完全没有提交和人气变动导致 30 天均无差异时，`rolling().std()` 必然引发 `NaN` 或抛出系统错误。安全守护表达式过滤规避了崩盘可能。

---

## ✅ 质量保证

### 测试执行记录
```bash
============= test session starts ==============
tests/strategies/test_eco_signal.py::test_eco_signal_neutral PASSED [ 33%]
tests/strategies/test_eco_signal.py::test_eco_signal_extreme_spike PASSED [ 66%]
tests/strategies/test_eco_signal.py::test_eco_signal_dominant_factor PASSED [100%]

============== 3 passed in 0.97s ===============
```

### 代码质量检查结果
| 检查项 | 结果 | 详情 |
|--------|------|------|
| 强统计学验证 | ✅ 通过 | 修正了在 30 日周期内 3 天突增在统计理论上最多造成 2.94 Z-score 的硬上限，转而符合严格 3-Sigma 原理的 `EXRTERME` 触发逻辑测试。 |
| Pandas 执行流 | ✅ 通过 | 没有任何 for 操作被使用于百万条时间戳迭代之上。 |

---

## 📝 总结/下一步
- [x] Story 17.5 顺利结项。这标志着另类数据的 **分析脑** 已经形成。
- [ ] 开启 Story 17.6: `信号注入选股流程`。我们将在 `quant-strategy` 的多维度选股漏斗中，针对具有技术生态加持标签的公司应用选股权重赋能！
