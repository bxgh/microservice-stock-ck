# EPIC-GSF Part 2: Analyzer Layer 核心分析器

**父文档**: [epic_gsf_master.md](./epic_gsf_master.md)  
**状态**: 📝 规划中

---

## 1. 目标

实现日K级别的6个核心分析器，遵循纯计算、无IO、可测试的原则。

---

## 2. User Stories

### Story 2.1: VolatilityAnalyzer
- **输入**: `pd.DataFrame` (K线: date, open, high, low, close, volume)
- **输出**: `VolatilityMetrics`
  ```python
  @dataclass
  class VolatilityMetrics:
      annual_volatility: float    # 年化波动率
      avg_amplitude: float        # 日均振幅
      max_amplitude: float        # 极限振幅
  ```
- **验收标准**: 单元测试覆盖标准差计算逻辑

### Story 2.2: DrawdownAnalyzer
- **输入**: `pd.DataFrame` (K线)
- **输出**: `DrawdownMetrics`
  ```python
  @dataclass
  class DrawdownMetrics:
      first_peak: float           # 首波峰值
      first_trough: float         # 首波谷底
      drawdown_pct: float         # 回撤幅度
      peak_days: int              # 峰值达成天数
      trough_days: int            # 谷底达成天数
  ```
- **验收标准**: 能正确识别峰谷拐点

### Story 2.3: MultiplesAnalyzer
- **输入**: K线 + `issue_price: Decimal`
- **输出**: `MultiplesMetrics`
  ```python
  @dataclass
  class MultiplesMetrics:
      first_wave_gain: float      # 首波涨幅
      high_to_issue: float        # 历史最高/发行价
      current_to_issue: float     # 当前/发行价
  ```
- **验收标准**: 发行价非 None 时计算正确

### Story 2.4: BetaCalculator
- **输入**: 个股K线 + 指数K线
- **输出**: `BetaMetrics`
  ```python
  @dataclass
  class BetaMetrics:
      beta: float                 # Beta 系数
      category: str               # 进攻型/跟随型/独立型
  ```
- **验收标准**: Beta 计算与 Excel 手算结果一致

### Story 2.5: LiquidityProfiler
- **输入**: K线 (含 turnover 字段)
- **输出**: `LiquidityMetrics`
  ```python
  @dataclass
  class LiquidityMetrics:
      avg_turnover: float         # 平均换手率
      recent_turnover: float      # 近期换手率
      decay_rate: float           # 换手衰减率
      hot_days: int               # 高活跃天数
  ```
- **验收标准**: decay_rate 计算逻辑正确

### Story 2.6: RecoveryAnalyzer
- **输入**: K线 + 峰谷数据
- **输出**: `RecoveryMetrics`
  ```python
  @dataclass
  class RecoveryMetrics:
      is_recovered: bool          # 是否复苏
      recovery_days: Optional[int] # 复苏天数
  ```
- **验收标准**: 对未复苏股票返回 None

---

## 3. 技术规范

- **无 IO**: 分析器不访问数据库/网络
- **向量化**: 使用 Numpy/Pandas 向量运算
- **可测试**: 100% 单元测试覆盖

---

## 4. 文件结构

```
quant-strategy/src/analyzers/
├── __init__.py
├── interfaces.py           # IAnalyzer 接口
├── models.py               # Metrics dataclasses
├── volatility.py
├── drawdown.py
├── multiples.py
├── beta.py
├── liquidity.py
└── recovery.py
```
