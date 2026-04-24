## Epic 2: 核心指标引擎

### Epic 目标

实现四条预警信号 + CCI 合成指数的计算逻辑。**每条信号独立可测,可单独验证。**

### ⚠️ 关键依赖说明

**Story 2.4(横截面相关性)是整个项目的数学基石**,以下全部模块依赖它:
- CCI 合成公式的 α、β、γ、δ 四个分量都需要 ρ̄
- 六层分层监测每一层都需要计算 ρ̄
- 历史回测需要 ρ̄ 序列才能复现 CCI
- 仪表盘的核心图表之一就是 ρ̄ 时间序列

**如果 Story 2.4 未实现,整个项目等于没有开始。** 必须作为 MVP 最高优先级项目。

### Stories

---

#### Story 2.1: 信号 ① 波动率方差上升

**As a** 开发者
**I want** 实现波动率方差比信号
**So that** 可以检测市场临界前的方差放大现象

**技术实现:**

```python
# backend/src/cci_monitor/signals/variance.py
from __future__ import annotations
import numpy as np
import pandas as pd
from ..core.exceptions import InsufficientDataError

def compute_variance_rise(
    returns: pd.Series,
    short_window: int = 20,
    long_window: int = 60,
    threshold: float = 1.5,
    persist_days: int = 5,
) -> pd.DataFrame:
    """
    计算波动率方差上升信号.
    
    逻辑: 接近临界时,系统恢复变慢,相同外力激起更大振幅.
    表现为短期波动率超过长期基准.
    
    Args:
        returns: 日收益率序列(%), index 为 date
        short_window: 短期窗口, 默认 20 日
        long_window: 长期基准窗口, 默认 60 日
        threshold: 比值触发阈值
        persist_days: 连续触发天数要求
    
    Returns:
        DataFrame with columns:
            - short_vol: 短期年化波动率(%)
            - long_vol:  长期年化波动率(%)
            - ratio:     short_vol / long_vol
            - triggered: 是否触发(ratio > threshold 持续 persist_days 日)
    
    Raises:
        InsufficientDataError: 如果 returns 长度小于 long_window
    """
    if len(returns) < long_window:
        raise InsufficientDataError(
            f"need at least {long_window} bars, got {len(returns)}"
        )
    
    short_vol = returns.rolling(short_window).std() * np.sqrt(252)
    long_vol = returns.rolling(long_window).std() * np.sqrt(252)
    ratio = short_vol / long_vol
    
    # 连续 persist_days 日大于阈值才算触发
    above = (ratio > threshold).astype(int)
    persist = above.rolling(persist_days).sum() >= persist_days
    
    return pd.DataFrame({
        'short_vol': short_vol,
        'long_vol': long_vol,
        'ratio': ratio,
        'triggered': persist,
    })
```

**验收标准:**
- [ ] 输入长度不足抛 `InsufficientDataError`
- [ ] 输出 DataFrame 的 index 与输入一致
- [ ] 前 `long_window` 行的输出为 NaN(符合 rolling 语义)
- [ ] 单元测试:
  - 常数收益率 → ratio 稳定在 1.0 附近,无触发
  - 波动突然放大 3 倍 → 5 日后触发
  - 长度正好等于 long_window → 最后一行有值
- [ ] 性能:1000 个数据点计算 < 10ms

**预计工时:** 2 小时

**依赖:** Epic 0

---

#### Story 2.2: 信号 ② 自相关性

**As a** 开发者
**I want** 实现 AR(1) 自相关信号
**So that** 可以检测市场收益率的"可预测性上升"——临界慢化的直接推论

**技术实现:**

```python
# backend/src/cci_monitor/signals/autocorr.py
import pandas as pd
from ..core.exceptions import InsufficientDataError

def compute_autocorrelation(
    returns: pd.Series,
    window: int = 60,
    threshold: float = 0.15,
    min_periods: int = 10,
) -> pd.DataFrame:
    """
    计算滚动 AR(1) 自相关信号.
    
    Args:
        returns: 日收益率序列
        window: 滚动窗口(默认 60 日)
        threshold: 触发阈值(默认 0.15,健康市场接近 0)
        min_periods: 窗口内最少有效数据点
    
    Returns:
        DataFrame:
            - ar1: Lag-1 自相关系数
            - triggered: ar1 > threshold
    """
    if len(returns) < window:
        raise InsufficientDataError(
            f"need at least {window} bars, got {len(returns)}"
        )
    
    def ar1(x: pd.Series) -> float:
        x = x.dropna()
        if len(x) < min_periods:
            return float('nan')
        return x.autocorr(lag=1)
    
    ar1_series = returns.rolling(window).apply(ar1, raw=False)
    
    return pd.DataFrame({
        'ar1': ar1_series,
        'triggered': ar1_series > threshold,
    })
```

**验收标准:**
- [ ] 白噪音序列 → ar1 ≈ 0(|ar1| < 0.1)
- [ ] 强自相关序列(r_t = 0.5 × r_{t-1} + ε) → ar1 ≈ 0.5
- [ ] 数据不足抛 `InsufficientDataError`
- [ ] 单元测试覆盖所有边界

**预计工时:** 2 小时

**依赖:** Epic 0

---

#### Story 2.3: 信号 ③ 偏度信号

**As a** 开发者
**I want** 实现收益率偏度信号
**So that** 可以检测买卖力量结构的根本性变化

**技术实现:**

```python
# backend/src/cci_monitor/signals/skewness.py
import pandas as pd
from scipy import stats
from ..core.exceptions import InsufficientDataError

def compute_skewness_flip(
    returns: pd.Series,
    window: int = 60,
    threshold: float = 1.0,
    flip_threshold: float = 1.5,
    flip_window: int = 20,
) -> pd.DataFrame:
    """
    计算偏度及其翻转信号.
    
    逻辑: 健康市场偏度接近 0.
    偏度绝对值大 = 分布严重偏斜 → 买卖力量失衡.
    偏度快速翻转 = 市场性质根本变化.
    
    Args:
        returns: 日收益率序列
        window: 计算偏度的滚动窗口
        threshold: 偏度绝对值阈值
        flip_threshold: 翻转变化幅度阈值
        flip_window: 翻转检测窗口
    
    Returns:
        DataFrame:
            - skewness: 滚动偏度
            - skew_change: 相比 flip_window 日前的变化
            - triggered: 绝对值超阈 OR 翻转超阈
    """
    if len(returns) < window:
        raise InsufficientDataError(
            f"need at least {window} bars, got {len(returns)}"
        )
    
    skew_series = returns.rolling(window).skew()
    skew_change = skew_series.diff(flip_window)
    
    triggered = (skew_series.abs() > threshold) | (skew_change.abs() > flip_threshold)
    
    return pd.DataFrame({
        'skewness': skew_series,
        'skew_change': skew_change,
        'triggered': triggered,
    })
```

**验收标准:**
- [ ] 正态分布样本 → 偏度接近 0
- [ ] 右偏分布(指数分布)→ 偏度 > 1
- [ ] 偏度从 -1 变为 +1(翻转幅度 2)→ triggered=True
- [ ] 单元测试覆盖

**预计工时:** 2 小时

**依赖:** Epic 0

---

#### Story 2.4: 信号 ④ 横截面相关性 ⭐⭐⭐ **整个项目的基石**

> ⚠️ **这是 MVP 的最高优先级 Story,也是整个项目中技术难度、性能要求、业务价值最高的单个 Story。**
>
> **所有 CCI 计算、分层监测、历史回测、仪表盘核心图表都依赖它。**
>
> **建议留出完整 1-2 天时间集中开发,不要碎片化推进。**

**As a** 开发者
**I want** 高性能地计算多股票横截面相关性 ρ̄
**So that** 我可以检测市场个股独立定价能力的消失——临界状态最敏感的前兆

**业务价值:**

横截面相关性 ρ̄ 是 A 股临界预警中**最敏感的单一信号**。其核心逻辑:
- 正常市场:个股基于自身基本面/资金面独立定价 → ρ̄ 低(0.2-0.35)
- 临界状态:某个主导因子(流动性/恐慌/量化)压过个股特质 → ρ̄ 升(>0.5)
- 相变时刻:ρ̄ 可能突破 0.65+,表明所有股票被同一因子拖拽

这是其他三条信号都无法替代的独特维度。

**技术规范:**

```python
# backend/src/cci_monitor/signals/correlation.py
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Literal
from ..core.exceptions import InsufficientDataError, SignalError
from ..core.logger import logger


@dataclass(frozen=True)
class CrossCorrelationResult:
    """横截面相关性完整结果."""
    rho_bar: pd.Series       # 总体 ρ̄
    rho_up: pd.Series        # 涨日 ρ̄
    rho_down: pd.Series      # 跌日 ρ̄
    delta_rho: pd.Series     # Δρ̄ = ρ̄(t) - ρ̄(t-20)
    up_down_ratio: pd.Series # ρ̄_down / ρ̄_up
    pattern: pd.Series       # 形态分类
    sample_size: pd.Series   # 每日实际用于计算的股票数


def compute_rho_bar_fast(
    returns_matrix: np.ndarray,
    window: int = 20,
    min_stocks: int = 10,
    min_valid_ratio: float = 0.8,
) -> np.ndarray:
    """
    ⭐ 核心实现 · 矢量化横截面相关性计算.
    
    关键约束:
    - 必须使用 numpy 矢量化,不能用 pandas.corr() 循环
    - 300 股 × 250 天性能必须 < 3 秒
    - 正确处理 NaN 值和 std=0 的退化情况
    
    Args:
        returns_matrix: (T, N) numpy 数组, T=天数, N=股票数
        window: 滚动窗口
        min_stocks: 窗口内有效股票数下限
        min_valid_ratio: 单股票在窗口内的数据完整率要求
    
    Returns:
        (T,) 数组, 前 window 个为 NaN
    
    算法步骤(每个时间点 t):
        1. 取窗口数据 R = returns_matrix[t-window:t]
        2. 筛选完整率 ≥ min_valid_ratio 的股票列
        3. 标准化: (x - mean) / std,处理 std=0 情况
        4. 相关矩阵 = X^T @ X / (window - 1)
        5. 取上三角(不含对角)均值 → ρ̄(t)
    """
    T, N = returns_matrix.shape
    result = np.full(T, np.nan)
    
    if T < window:
        return result
    
    for t in range(window, T):
        win = returns_matrix[t-window:t]
        
        valid_ratio_per_col = np.isfinite(win).sum(axis=0) / window
        col_mask = valid_ratio_per_col >= min_valid_ratio
        
        if col_mask.sum() < min_stocks:
            continue
        
        win_filtered = win[:, col_mask]
        mean = np.nanmean(win_filtered, axis=0)
        centered = win_filtered - mean
        std = np.nanstd(centered, axis=0)
        std_valid = std > 1e-10
        if std_valid.sum() < min_stocks:
            continue
        
        X = centered[:, std_valid] / std[std_valid]
        X = np.nan_to_num(X, nan=0.0)
        n_valid = std_valid.sum()
        corr = (X.T @ X) / (window - 1)
        mask = np.triu(np.ones((n_valid, n_valid), dtype=bool), k=1)
        result[t] = corr[mask].mean()
    
    return result


def compute_cross_correlation(
    returns_wide: pd.DataFrame,
    window: int = 20,
    min_stocks: int = 10,
) -> CrossCorrelationResult:
    """
    完整的横截面相关性计算.
    包含 ρ̄ 主序列、分方向 ρ̄、Δρ̄、形态分类.
    
    详细说明参见 Technical Spec.
    """
    if len(returns_wide) < window + 20:
        raise InsufficientDataError(
            f"need at least {window + 20} bars, got {len(returns_wide)}"
        )
    
    dates = returns_wide.index
    returns_matrix = returns_wide.values
    
    rho_bar_arr = compute_rho_bar_fast(returns_matrix, window, min_stocks)
    rho_bar = pd.Series(rho_bar_arr, index=dates, name='rho_bar')
    
    market_ret = returns_wide.mean(axis=1)
    
    # 分方向计算 rho_up / rho_down
    rho_up_list = []
    rho_down_list = []
    for t in range(len(dates)):
        if t < window:
            rho_up_list.append(np.nan)
            rho_down_list.append(np.nan)
            continue
        
        win_ret = market_ret.iloc[t-window:t]
        win_data = returns_wide.iloc[t-window:t]
        
        up_mask = win_ret > 0
        down_mask = win_ret < 0
        
        if up_mask.sum() >= 5:
            rho_up_list.append(_compute_rho_single(win_data[up_mask].values, min_stocks))
        else:
            rho_up_list.append(np.nan)
        
        if down_mask.sum() >= 5:
            rho_down_list.append(_compute_rho_single(win_data[down_mask].values, min_stocks))
        else:
            rho_down_list.append(np.nan)
    
    rho_up = pd.Series(rho_up_list, index=dates, name='rho_up')
    rho_down = pd.Series(rho_down_list, index=dates, name='rho_down')
    
    delta_rho = rho_bar.diff(20)
    up_down_ratio = rho_down / rho_up
    pattern = _classify_patterns(rho_bar, market_ret, returns_wide)
    sample_size = returns_wide.notna().sum(axis=1)
    
    return CrossCorrelationResult(
        rho_bar=rho_bar,
        rho_up=rho_up,
        rho_down=rho_down,
        delta_rho=delta_rho,
        up_down_ratio=up_down_ratio,
        pattern=pattern,
        sample_size=sample_size,
    )


def _compute_rho_single(data: np.ndarray, min_stocks: int = 10) -> float:
    """单窗口 ρ̄ 计算(用于分方向场景)."""
    if len(data) < 2:
        return float('nan')
    
    valid_ratio = np.isfinite(data).sum(axis=0) / len(data)
    col_mask = valid_ratio >= 0.8
    if col_mask.sum() < min_stocks:
        return float('nan')
    
    data_f = data[:, col_mask]
    mean = np.nanmean(data_f, axis=0)
    centered = data_f - mean
    std = np.nanstd(centered, axis=0)
    std_valid = std > 1e-10
    if std_valid.sum() < min_stocks:
        return float('nan')
    
    X = centered[:, std_valid] / std[std_valid]
    X = np.nan_to_num(X, nan=0.0)
    n = std_valid.sum()
    corr = (X.T @ X) / (len(data_f) - 1)
    mask = np.triu(np.ones((n, n), dtype=bool), k=1)
    return float(corr[mask].mean())


def _classify_patterns(
    rho_bar: pd.Series,
    market_ret: pd.Series,
    returns_wide: pd.DataFrame,
    high_rho_threshold: float = 0.45,
    rally_return_threshold: float = 0.3,
    crash_return_threshold: float = -0.3,
) -> pd.Series:
    """
    形态分类: 
        A_rally    - 齐涨型(ρ̄ 高 + 市场涨)       · 健康,介质变深
        B_crash    - 齐跌型(ρ̄ 高 + 市场跌)       · 恐慌,相变警报
        C_crowding - 齐震型(ρ̄ 高 + 市场横盘)     · 拥挤,定时炸弹
        normal     - 正常
    """
    market_5d = market_ret.rolling(5).mean()
    pattern = pd.Series('normal', index=rho_bar.index, dtype=object)
    high_rho = rho_bar > high_rho_threshold
    
    pattern[high_rho & (market_5d > rally_return_threshold)] = 'A_rally'
    pattern[high_rho & (market_5d < crash_return_threshold)] = 'B_crash'
    pattern[high_rho & (market_5d.abs() <= rally_return_threshold)] = 'C_crowding'
    
    return pattern
```

**正确性验证测试:**

```python
# tests/unit/test_correlation.py
import numpy as np
from cci_monitor.signals.correlation import compute_rho_bar_fast, compute_cross_correlation

def test_rho_bar_independent_stocks():
    """独立随机序列 ρ̄ 应接近 0."""
    np.random.seed(42)
    returns = np.random.randn(250, 50)
    rho = compute_rho_bar_fast(returns, window=20)
    valid_rho = rho[~np.isnan(rho)]
    assert abs(np.mean(valid_rho)) < 0.1

def test_rho_bar_synchronized_stocks():
    """完全同步序列 ρ̄ 应接近 1."""
    base = np.random.randn(250, 1)
    returns = np.tile(base, (1, 50))
    rho = compute_rho_bar_fast(returns, window=20)
    valid_rho = rho[~np.isnan(rho)]
    assert np.mean(valid_rho) > 0.95

def test_rho_bar_partial_correlation():
    """有明显相关性但非完全同步."""
    np.random.seed(0)
    common = np.random.randn(250, 1)
    idiosync = np.random.randn(250, 50)
    returns = 0.5 * common + 0.5 * idiosync
    rho = compute_rho_bar_fast(returns, window=20)
    mean_rho = np.mean(rho[~np.isnan(rho)])
    assert 0.4 < mean_rho < 0.6

def test_rho_bar_handles_nans():
    """部分 NaN 不崩溃."""
    returns = np.random.randn(250, 50)
    returns[:100, :10] = np.nan
    rho = compute_rho_bar_fast(returns, window=20)
    assert not np.isnan(rho[-1])
```

**性能基准测试:**

```python
# tests/unit/test_correlation_performance.py
import numpy as np
import time
import pytest

@pytest.mark.benchmark
def test_performance_300x250():
    """核心基准: 300 股 × 250 天 < 3 秒."""
    np.random.seed(42)
    returns = np.random.randn(250, 300)
    t0 = time.time()
    rho = compute_rho_bar_fast(returns, window=20)
    elapsed = time.time() - t0
    assert elapsed < 3.0, f"性能未达标: {elapsed:.2f}s"
```

**真实数据验证:**

```python
# tests/integration/test_correlation_real_data.py
@pytest.mark.integration
async def test_real_hs300_rho_bar_range():
    """真实沪深300 ρ̄ 应在 0.1-0.8 之间."""
    source = AkshareDataSource()
    codes = (await source.fetch_index_components('000300'))[:50]
    returns_wide = await source.fetch_stocks_batch(codes, date.today() - timedelta(days=365))
    result = compute_cross_correlation(returns_wide, window=20)
    rho_clean = result.rho_bar.dropna()
    assert 0.05 < rho_clean.min() < rho_clean.max() < 0.85
    assert 0.15 < rho_clean.mean() < 0.65
```

**验收标准(严格):**

**功能正确性(必须全部通过):**
- [ ] 独立随机序列测试:|平均 ρ̄| < 0.1
- [ ] 完全同步序列测试:平均 ρ̄ > 0.95
- [ ] 50/50 混合因子测试:0.4 < 平均 ρ̄ < 0.6(理论值 0.5)
- [ ] NaN 容错测试通过
- [ ] 有效股票数不足时返回 NaN 不抛异常
- [ ] `CrossCorrelationResult` 所有字段都有正确计算
- [ ] 形态分类(A/B/C/normal)逻辑正确

**性能(硬性要求):**
- [ ] ⭐ **300 股 × 250 天计算 < 3 秒**(核心要求)
- [ ] 500 股 × 500 天计算 < 10 秒
- [ ] 内存使用合理,无泄漏
- [ ] 无 pandas.corr() 循环调用

**集成验证:**
- [ ] 用真实沪深300数据计算,结果在合理区间
- [ ] 能识别出 2024.01 微盘崩盘、2024.09 政策反弹等历史形态
- [ ] 三种形态(A/B/C)都能被正确标注

**代码质量:**
- [ ] 完整类型注解
- [ ] 完整 docstring 包含 Args/Returns/Raises/Example
- [ ] 关键算法步骤有中文注释
- [ ] 通过 ruff 和 mypy 检查

**预计工时:** **8-12 小时**(分 2 天集中开发,不要碎片化)

**分阶段开发建议:**

| 小时数 | 任务 |
|---|---|
| 0-2h | 读懂算法,跑通 `compute_rho_bar_fast` 主函数 |
| 2-4h | 写正确性单元测试,验证三种边界情况 |
| 4-6h | 性能优化,确保达到 3 秒基准 |
| 6-8h | 实现 `compute_cross_correlation` 完整版(含分方向) |
| 8-10h | 实现形态分类 `_classify_patterns` |
| 10-12h | 真实数据集成测试 + 可视化验证 |

**依赖:** Story 1.2(需要 akshare 拉取真实数据验证)

**下游依赖(都阻塞在本 Story):**
- Story 2.5 CCI 合成(使用 ρ̄ 和分方向 ρ̄)
- Story 3.2-3.7 六层分层(每层都要计算 ρ̄)
- Story 4.2 回测引擎(需要历史 ρ̄ 序列)
- Story 5.4 主仪表盘(ρ̄ 是核心图表)

---

#### Story 2.5: CCI 合成指数

**As a** 开发者
**I want** 将四条信号合成为单一 CCI 数值
**So that** 可以给出直观的 0-2 区间预警指标

**技术实现:**

```python
# backend/src/cci_monitor/signals/cci.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from ..core.exceptions import ConfigurationError


@dataclass(frozen=True)
class CCIResult:
    date: date
    cci: float
    alpha: float
    beta: float
    gamma: float
    delta: float
    alert_level: int
    alert_label: str
    market_rho: float
    resonant_rho: float | None
    deep_rho: float | None
    delta_rho: float | None
    up_down_ratio: float | None
    computed_at: datetime


def compute_cci(
    market_rho: float,
    resonant_rho: float | None = None,
    deep_rho: float | None = None,
    delta_rho: float | None = None,
    up_down_ratio: float | None = None,
    weights: dict[str, float] | None = None,
    computed_for_date: date | None = None,
) -> CCIResult:
    """
    计算 CCI 合成指数.
    
    公式:
        CCI = α_weight × (market_rho / 0.5)
            + β_weight × max(resonant_rho / deep_rho, 1.0)
            + γ_weight × max(delta_rho / 0.15, 0)
            + δ_weight × max(up_down_ratio, 1.0)
    """
    w = weights or {'alpha': 0.4, 'beta': 0.3, 'gamma': 0.2, 'delta': 0.1}
    
    if abs(sum(w.values()) - 1.0) > 1e-6:
        raise ConfigurationError(
            f"weights must sum to 1.0, got {sum(w.values())}"
        )
    
    alpha = w['alpha'] * (market_rho / 0.5)
    
    if resonant_rho is not None and deep_rho is not None and deep_rho > 1e-6:
        beta = w['beta'] * max(resonant_rho / deep_rho, 1.0)
    else:
        beta = w['beta']
    
    if delta_rho is not None:
        gamma = w['gamma'] * max(delta_rho / 0.15, 0)
    else:
        gamma = 0.0
    
    if up_down_ratio is not None:
        delta = w['delta'] * max(up_down_ratio, 1.0)
    else:
        delta = w['delta']
    
    cci = alpha + beta + gamma + delta
    alert_level, alert_label = classify_alert_level(cci)
    
    return CCIResult(
        date=computed_for_date or date.today(),
        cci=round(cci, 4),
        alpha=round(alpha, 4),
        beta=round(beta, 4),
        gamma=round(gamma, 4),
        delta=round(delta, 4),
        alert_level=alert_level,
        alert_label=alert_label,
        market_rho=market_rho,
        resonant_rho=resonant_rho,
        deep_rho=deep_rho,
        delta_rho=delta_rho,
        up_down_ratio=up_down_ratio,
        computed_at=datetime.now(),
    )


def classify_alert_level(cci: float) -> tuple[int, str]:
    if cci < 0.7:  return 0, "安全"
    if cci < 1.0:  return 1, "关注"
    if cci < 1.3:  return 2, "警戒"
    else:          return 3, "临界"
```

**验收标准:**
- [ ] baseline 场景(market_rho=0.25, resonant/deep=0.78, delta=0.05, ratio=1.1):CCI 在 0.5-0.9
- [ ] 临界场景(market_rho=0.65, resonant/deep=1.33, delta=0.20, ratio=1.8):CCI > 1.3 且 alert_level=3
- [ ] 权重和不为 1 → 抛 `ConfigurationError`
- [ ] 缺失可选参数使用中性值

**预计工时:** 3 小时

**依赖:** Story 2.4

---

#### Story 2.6: 每日计算服务(⭐ Milestone 2 Checkpoint)

**As a** 开发者
**I want** 一个完整的 daily_service 把前面的东西串起来
**So that** 能从命令行跑一次完整流程并把 CCI 入库

**技术实现:**

```python
# backend/src/cci_monitor/services/daily_service.py
from datetime import date, timedelta
from ..data.akshare_source import AkshareDataSource
from ..data.cache import CachedDataSource, Cache
from ..signals.correlation import compute_cross_correlation
from ..signals.cci import compute_cci, CCIResult
from ..db.models import CCIRecord
from ..core.database import get_db_session
from ..core.logger import logger
from config.settings import get_settings


class DailyService:
    def __init__(self):
        settings = get_settings()
        cache = Cache(settings.data.cache_dir, settings.data.cache_ttl_hours)
        self.source = CachedDataSource(AkshareDataSource(), cache)
        self.settings = settings
    
    async def run_daily(self, target_date: date | None = None) -> CCIResult:
        target_date = target_date or date.today()
        logger.info("Starting daily computation for {date}", date=target_date)
        
        start_date = target_date - timedelta(days=120)
        
        # 1. 拉取成分股
        codes = await self.source.fetch_index_components('000300')
        top_codes = codes[:self.settings.signal.correlation_stock_count]
        
        # 2. 批量拉取
        returns_wide = await self.source.fetch_stocks_batch(top_codes, start_date, target_date)
        
        # 3. 横截面相关性
        cc_result = compute_cross_correlation(
            returns_wide,
            window=self.settings.signal.correlation_window,
        )
        
        # 4. 取最新一天的指标
        market_rho = float(cc_result.rho_bar.iloc[-1])
        delta_rho = float(cc_result.delta_rho.iloc[-1]) if not cc_result.delta_rho.iloc[-1] != cc_result.delta_rho.iloc[-1] else None
        up = cc_result.rho_up.iloc[-1]
        down = cc_result.rho_down.iloc[-1]
        up_down_ratio = float(down / up) if up > 0 else None
        
        # 5. 合成 CCI
        cci_result = compute_cci(
            market_rho=market_rho,
            delta_rho=delta_rho,
            up_down_ratio=up_down_ratio,
            computed_for_date=target_date,
        )
        logger.info("CCI={cci} {label}", cci=cci_result.cci, label=cci_result.alert_label)
        
        # 6. 写入数据库
        async with get_db_session() as session:
            record = CCIRecord(
                date=cci_result.date,
                layer_id=1,
                cci=cci_result.cci,
                alpha=cci_result.alpha,
                beta=cci_result.beta,
                gamma=cci_result.gamma,
                delta=cci_result.delta,
                alert_level=cci_result.alert_level,
                alert_label=cci_result.alert_label,
                market_rho=cci_result.market_rho,
                delta_rho=cci_result.delta_rho,
                up_down_ratio=cci_result.up_down_ratio,
                computed_at=cci_result.computed_at,
            )
            session.add(record)
        
        return cci_result
```

**CLI 入口:**

```python
# backend/scripts/run_daily.py
import asyncio
from cci_monitor.services.daily_service import DailyService
from cci_monitor.core.logger import setup_logging

async def main():
    setup_logging()
    service = DailyService()
    result = await service.run_daily()
    print(f"\n=== 今日 CCI ===")
    print(f"日期: {result.date}")
    print(f"CCI:  {result.cci}")
    print(f"等级: {result.alert_label}")
    print(f"α={result.alpha} β={result.beta} γ={result.gamma} δ={result.delta}")

if __name__ == "__main__":
    asyncio.run(main())
```

**验收标准(⭐ Milestone 2 Checkpoint):**
- [ ] 运行 `python scripts/run_daily.py` 完整流程无错误
- [ ] 输出今日 CCI 数值在合理范围(0-2)
- [ ] 数据库 `cci_records` 表有新记录
- [ ] 运行两次不会重复插入(UniqueConstraint 生效)
- [ ] 全流程耗时 < 5 分钟(含数据拉取)

**预计工时:** 3 小时

**依赖:** Story 2.4, 2.5, 1.2, 1.3, 0.5

---

