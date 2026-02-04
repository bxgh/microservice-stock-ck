# 回测验证框架

## 1. 概述

策略有效性验证框架，包含回测周期设计、收益度量、参数敏感性测试。

---

## 2. 回测周期设计

### 2.1 滚动窗口

```
┌─────────────────────────────────────────────────────────────────┐
│                    60交易日                    20交易日          │
│  ├─────────────────────────────────────────────┼───────────────┤ │
│  │              训练期                          │   验证期      │ │
│  │         (参数优化、模型训练)                   │  (样本外测试)  │ │
│  └─────────────────────────────────────────────┴───────────────┘ │
│                                                                  │
│  每5个交易日滚动一次                                               │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 配置

```python
@dataclass
class BacktestConfig:
    train_days: int = 60  # 训练期长度
    test_days: int = 20  # 验证期长度
    roll_days: int = 5  # 滚动步长
    
    # 交易成本
    commission_rate: float = 0.0003  # 万三
    slippage_rate: float = 0.001  # 千一滑点
    stamp_tax_rate: float = 0.001  # 印花税（卖出）
    
    # 仓位
    max_position_per_stock: float = 0.1  # 单股最大仓位10%
    max_total_position: float = 0.8  # 总仓位上限80%
```

---

## 3. 收益度量

### 3.1 核心指标

| 指标 | 公式 | 说明 |
|------|------|------|
| **绝对收益率** | $\frac{V_{end} - V_{start}}{V_{start}}$ | 区间总收益 |
| **年化收益率** | $(1 + R)^{252/n} - 1$ | 年化换算 |
| **超额收益** | $R_{strategy} - R_{benchmark}$ | 相对沪深300 |
| **夏普比率** | $\frac{R - R_f}{\sigma}$ | 风险调整收益 |
| **最大回撤** | $\max\limits_{t}(\frac{Peak_t - V_t}{Peak_t})$ | 最大亏损幅度 |
| **胜率** | $\frac{盈利交易数}{总交易数}$ | 盈利概率 |
| **盈亏比** | $\frac{平均盈利}{平均亏损}$ | 赔率 |

### 3.2 计算实现

```python
import numpy as np
import pandas as pd

class BacktestMetrics:
    """
    回测指标计算
    """
    def __init__(
        self, 
        returns: pd.Series,  # 日收益率序列
        benchmark_returns: pd.Series,  # 基准收益率
        risk_free_rate: float = 0.03 / 252  # 日无风险利率
    ):
        self.returns = returns
        self.benchmark = benchmark_returns
        self.rf = risk_free_rate
    
    def total_return(self) -> float:
        """总收益率"""
        return (1 + self.returns).prod() - 1
    
    def annualized_return(self) -> float:
        """年化收益率"""
        n = len(self.returns)
        total = self.total_return()
        return (1 + total) ** (252 / n) - 1
    
    def excess_return(self) -> float:
        """超额收益（相对基准）"""
        strategy_return = self.total_return()
        benchmark_return = (1 + self.benchmark).prod() - 1
        return strategy_return - benchmark_return
    
    def sharpe_ratio(self) -> float:
        """夏普比率"""
        excess = self.returns - self.rf
        if excess.std() == 0:
            return 0.0
        return excess.mean() / excess.std() * np.sqrt(252)
    
    def max_drawdown(self) -> float:
        """最大回撤"""
        cumulative = (1 + self.returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (running_max - cumulative) / running_max
        return drawdown.max()
    
    def win_rate(self, trades: pd.DataFrame) -> float:
        """胜率"""
        winning = len(trades[trades['pnl'] > 0])
        total = len(trades)
        return winning / total if total > 0 else 0.0
    
    def profit_loss_ratio(self, trades: pd.DataFrame) -> float:
        """盈亏比"""
        winners = trades[trades['pnl'] > 0]['pnl'].mean()
        losers = abs(trades[trades['pnl'] < 0]['pnl'].mean())
        if losers == 0:
            return float('inf')
        return winners / losers
    
    def report(self, trades: pd.DataFrame = None) -> dict:
        """生成完整报告"""
        result = {
            "total_return": self.total_return(),
            "annualized_return": self.annualized_return(),
            "excess_return": self.excess_return(),
            "sharpe_ratio": self.sharpe_ratio(),
            "max_drawdown": self.max_drawdown(),
            "volatility": self.returns.std() * np.sqrt(252),
        }
        
        if trades is not None:
            result["win_rate"] = self.win_rate(trades)
            result["profit_loss_ratio"] = self.profit_loss_ratio(trades)
            result["total_trades"] = len(trades)
        
        return result
```

---

## 4. 回测引擎

### 4.1 交易模拟器

```python
@dataclass
class Position:
    stock_code: str
    shares: int
    entry_price: float
    entry_date: str

@dataclass
class Trade:
    stock_code: str
    direction: str  # 'BUY' / 'SELL'
    shares: int
    price: float
    date: str
    pnl: float = 0.0
    
class BacktestEngine:
    """
    回测引擎
    """
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.cash = 1_000_000  # 初始资金100万
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self.daily_values: list[float] = []
    
    def get_portfolio_value(self, prices: dict[str, float]) -> float:
        """计算组合总价值"""
        position_value = sum(
            pos.shares * prices.get(code, pos.entry_price)
            for code, pos in self.positions.items()
        )
        return self.cash + position_value
    
    def execute_signal(
        self, 
        signal: TickClusterSignal, 
        current_prices: dict[str, float]
    ):
        """执行交易信号"""
        code = signal.stock_code
        price = current_prices.get(code, signal.price)
        
        # 滑点
        if signal.direction == 'BUY':
            price *= (1 + self.config.slippage_rate)
        else:
            price *= (1 - self.config.slippage_rate)
        
        if signal.direction == 'BUY':
            self._buy(code, price, signal)
        elif signal.direction == 'SELL':
            self._sell(code, price, signal)
    
    def _buy(self, code: str, price: float, signal: TickClusterSignal):
        """买入"""
        portfolio_value = self.get_portfolio_value({code: price})
        max_value = portfolio_value * self.config.max_position_per_stock
        
        # 计算可买股数
        available_cash = self.cash * 0.95  # 留5%现金
        buy_value = min(available_cash, max_value) * signal.strength
        shares = int(buy_value / price / 100) * 100  # 整百股
        
        if shares == 0:
            return
        
        cost = shares * price * (1 + self.config.commission_rate)
        
        if cost > self.cash:
            return
        
        self.cash -= cost
        self.positions[code] = Position(
            stock_code=code,
            shares=shares,
            entry_price=price,
            entry_date=signal.timestamp.strftime('%Y-%m-%d')
        )
        
        self.trades.append(Trade(
            stock_code=code,
            direction='BUY',
            shares=shares,
            price=price,
            date=signal.timestamp.strftime('%Y-%m-%d')
        ))
    
    def _sell(self, code: str, price: float, signal: TickClusterSignal):
        """卖出"""
        if code not in self.positions:
            return
        
        pos = self.positions[code]
        proceeds = pos.shares * price * (1 - self.config.commission_rate - self.config.stamp_tax_rate)
        pnl = proceeds - pos.shares * pos.entry_price * (1 + self.config.commission_rate)
        
        self.cash += proceeds
        del self.positions[code]
        
        self.trades.append(Trade(
            stock_code=code,
            direction='SELL',
            shares=pos.shares,
            price=price,
            date=signal.timestamp.strftime('%Y-%m-%d'),
            pnl=pnl
        ))
    
    def record_daily_value(self, prices: dict[str, float]):
        """记录每日组合价值"""
        self.daily_values.append(self.get_portfolio_value(prices))
    
    def get_returns(self) -> pd.Series:
        """计算日收益率序列"""
        values = pd.Series(self.daily_values)
        returns = values.pct_change().dropna()
        return returns
```

### 4.2 回测流程

```python
async def run_backtest(
    start_date: str,
    end_date: str,
    config: BacktestConfig
) -> dict:
    """
    执行回测
    """
    engine = BacktestEngine(config)
    dates = get_trading_dates(start_date, end_date)
    
    for date in dates:
        # 1. 加载历史信号
        signals = load_signals(date)
        
        # 2. 加载当日价格
        prices = load_prices(date)
        
        # 3. 执行信号
        for signal in signals:
            engine.execute_signal(signal, prices)
        
        # 4. 记录收盘价值
        engine.record_daily_value(prices)
    
    # 5. 计算指标
    returns = engine.get_returns()
    benchmark = load_benchmark_returns(start_date, end_date)
    
    metrics = BacktestMetrics(returns, benchmark)
    trades_df = pd.DataFrame([asdict(t) for t in engine.trades])
    
    return metrics.report(trades_df)
```

---

## 5. 参数敏感性测试

### 5.1 测试维度

| 参数 | 测试范围 | 步长 |
|------|----------|------|
| DTW窗口 | [5, 10, 15, 20, 30] | - |
| 阈值分位数 | [1%, 3%, 5%, 10%] | - |
| OBI权重衰减 | [线性, 指数, 均匀] | - |
| 融合权重α | [0.3, 0.4, 0.5, 0.6, 0.7] | 0.1 |
| 分歧度阈值 | [0.2, 0.3, 0.4] | 0.1 |

### 5.2 测试实现

```python
from itertools import product

async def parameter_sensitivity_test(
    start_date: str,
    end_date: str,
    base_config: BacktestConfig
) -> pd.DataFrame:
    """
    参数敏感性测试
    """
    # 参数组合
    dtw_windows = [5, 10, 15, 20, 30]
    thresholds = [0.01, 0.03, 0.05, 0.10]
    alpha_weights = [0.3, 0.4, 0.5, 0.6, 0.7]
    
    results = []
    
    for window, threshold, alpha in product(dtw_windows, thresholds, alpha_weights):
        # 设置参数
        set_dtw_window(window)
        set_threshold_percentile(threshold)
        set_fusion_weights((alpha, (1-alpha)*0.6, (1-alpha)*0.4))
        
        # 运行回测
        report = await run_backtest(start_date, end_date, base_config)
        
        results.append({
            "dtw_window": window,
            "threshold": threshold,
            "alpha": alpha,
            **report
        })
    
    return pd.DataFrame(results)
```

### 5.3 结果分析

```python
def analyze_sensitivity(results: pd.DataFrame) -> dict:
    """
    分析参数敏感性
    """
    # 按参数分组，计算均值和标准差
    by_window = results.groupby('dtw_window')['sharpe_ratio'].agg(['mean', 'std'])
    by_threshold = results.groupby('threshold')['sharpe_ratio'].agg(['mean', 'std'])
    by_alpha = results.groupby('alpha')['sharpe_ratio'].agg(['mean', 'std'])
    
    # 最优参数组合
    best_idx = results['sharpe_ratio'].idxmax()
    best_params = results.loc[best_idx, ['dtw_window', 'threshold', 'alpha']]
    
    return {
        "by_dtw_window": by_window.to_dict(),
        "by_threshold": by_threshold.to_dict(),
        "by_alpha": by_alpha.to_dict(),
        "best_params": best_params.to_dict(),
        "best_sharpe": results.loc[best_idx, 'sharpe_ratio'],
    }
```

---

## 6. 验证报告模板

```markdown
# TickCluster策略回测报告

## 1. 回测概况

| 项目 | 值 |
|------|-----|
| 回测区间 | 2025-01-01 ~ 2026-01-31 |
| 交易日数 | 242 |
| 初始资金 | ¥1,000,000 |
| 期末资金 | ¥1,245,678 |

## 2. 核心指标

| 指标 | 策略 | 沪深300 | 超额 |
|------|------|---------|------|
| 总收益率 | 24.57% | 12.34% | +12.23% |
| 年化收益率 | 26.12% | 13.08% | +13.04% |
| 夏普比率 | 1.45 | 0.78 | - |
| 最大回撤 | 8.23% | 15.67% | - |
| 胜率 | 58.3% | - | - |
| 盈亏比 | 1.82 | - | - |

## 3. 月度收益

| 月份 | 收益 | 基准 | 超额 |
|------|------|------|------|
| 2025-01 | 3.2% | 2.1% | +1.1% |
| ... | ... | ... | ... |

## 4. 参数敏感性

### DTW窗口影响

| 窗口 | 均值Sharpe | 标准差 | 稳定性 |
|------|------------|--------|--------|
| 15min | 1.45 | 0.12 | 高 |
| 30min | 1.38 | 0.18 | 中 |

### 最优参数组合

- DTW窗口: 15分钟
- 阈值分位数: 5%
- 融合权重α: 0.5

## 5. 风险分析

### 最大回撤区间

- 开始日期: 2025-05-10
- 结束日期: 2025-05-25
- 回撤幅度: 8.23%
- 恢复天数: 15

### 连续亏损

- 最大连亏天数: 7
- 最大连亏金额: ¥45,678
```

---

## 7. 配置

```yaml
backtest:
  # 周期设置
  train_days: 60
  test_days: 20
  roll_days: 5
  
  # 交易成本
  commission_rate: 0.0003
  slippage_rate: 0.001
  stamp_tax_rate: 0.001
  
  # 仓位管理
  max_position_per_stock: 0.1
  max_total_position: 0.8
  initial_capital: 1000000
  
  # 参数敏感性测试
  sensitivity:
    dtw_windows: [5, 10, 15, 20, 30]
    thresholds: [0.01, 0.03, 0.05, 0.10]
    alpha_weights: [0.3, 0.4, 0.5, 0.6, 0.7]
```
