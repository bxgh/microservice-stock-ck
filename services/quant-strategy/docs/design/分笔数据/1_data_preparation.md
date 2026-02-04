# 数据准备与边界条件处理

## 1. 数据输入

### 1.1 原始数据结构

**L1分笔数据** (`tick_data` 表)：
| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | String | 股票代码 |
| timestamp | DateTime64(3) | 时间戳（毫秒精度） |
| price | Float64 | 成交价 |
| volume | UInt64 | 成交量（股） |
| amount | Float64 | 成交额（元） |
| bid1/ask1 | Float64 | 买一/卖一价 |
| bid1_vol/ask1_vol | UInt64 | 买一/卖一量 |

**五档快照数据** (`order_book` 表)：
| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | String | 股票代码 |
| timestamp | DateTime64(3) | 时间戳 |
| bid1-5 / ask1-5 | Float64 | 五档买卖价 |
| bid1_vol-5_vol / ask1_vol-5_vol | UInt64 | 五档买卖量 |

---

## 2. 边界条件处理

### 2.1 涨跌停股处理

**问题**：涨停股买入强度被人为压缩（挂单无法成交），跌停股卖出强度同理。

**处理方案**：
```python
def detect_limit(price: float, prev_close: float) -> int:
    """
    检测涨跌停状态
    返回：1=涨停, -1=跌停, 0=正常
    """
    limit_up = prev_close * 1.10   # ST股需用1.05
    limit_down = prev_close * 0.90
    
    if abs(price - limit_up) < 0.01:
        return 1
    elif abs(price - limit_down) < 0.01:
        return -1
    return 0
```

**修正规则**：
| 状态 | 主动买入强度修正 |
|------|------------------|
| 涨停 | 强制设为 1.0（最大值） |
| 跌停 | 强制设为 0.0（最小值） |
| 正常 | 按公式计算 |

**标记字段**：
```python
df['limit_flag'] = df.apply(
    lambda row: detect_limit(row['price'], row['prev_close']), 
    axis=1
)
```

---

### 2.2 停牌股处理

**问题**：停牌当天无数据，序列长度不一致。

**处理方案**：
1. 从当日股票清单中剔除停牌股
2. 序列置空（不参与当日计算）
3. 记录停牌状态用于跨日分析

**检测逻辑**：
```python
def is_suspended(stock_code: str, date: str, tick_count: int) -> bool:
    """
    判断是否停牌
    tick_count: 当日分笔记录数
    正常交易日约4800条（240分钟×20条/分钟）
    """
    return tick_count < 100  # 阈值可调
```

---

### 2.3 集合竞价处理

**时间段**：
- 开盘集合竞价：09:15 - 09:25
- 尾盘集合竞价：14:57 - 15:00

**处理方案**：
1. **不计入连续竞价序列**：从240分钟序列中排除
2. **单独提取特征**：作为额外特征向量

**集合竞价特征**：
```python
def extract_auction_features(df: pd.DataFrame) -> dict:
    """
    提取集合竞价特征
    """
    # 开盘集合竞价
    open_auction = df[(df['time'] >= '09:15') & (df['time'] < '09:25')]
    
    # 尾盘集合竞价
    close_auction = df[(df['time'] >= '14:57') & (df['time'] <= '15:00')]
    
    return {
        'open_auction_volume': open_auction['volume'].sum(),
        'open_auction_amount': open_auction['amount'].sum(),
        'open_auction_vwap': open_auction['amount'].sum() / open_auction['volume'].sum(),
        'close_auction_volume': close_auction['volume'].sum(),
        'close_auction_amount': close_auction['amount'].sum(),
        'close_auction_vwap': close_auction['amount'].sum() / close_auction['volume'].sum(),
    }
```

---

### 2.4 午间休市处理

**时间段**：11:30 - 13:00

**问题**：90分钟断点导致序列不连续。

**处理方案**：
1. **不插值**：保持断点，上午120分钟 + 下午120分钟
2. **序列索引**：使用 0-239 分钟索引，而非实际时间
3. **跨午时间差**：DTW计算时自动处理

**分钟索引映射**：
```python
def map_to_minute_index(time_str: str) -> int:
    """
    将实际时间映射为分钟索引（0-239）
    """
    hour, minute = map(int, time_str.split(':'))
    
    if hour < 12:  # 上午 09:30-11:30
        return (hour - 9) * 60 + minute - 30
    else:  # 下午 13:00-15:00
        return 120 + (hour - 13) * 60 + minute
```

---

### 2.5 ST/退市警示股处理

**处理方案**：
- **保留参与计算**：ST股可能存在庄家行为，是目标发现对象
- **标记字段**：添加 `is_st` 标记
- **涨跌幅修正**：ST股涨跌停阈值为5%

```python
def get_limit_threshold(stock_code: str) -> float:
    """
    获取涨跌停阈值
    ST股：5%，普通股：10%，科创/创业板：20%
    """
    if stock_code.startswith(('688', '300')):
        return 0.20
    elif is_st_stock(stock_code):
        return 0.05
    return 0.10
```

---

## 3. 数据清洗流程

```python
def clean_tick_data(date: str) -> pd.DataFrame:
    """
    数据清洗主流程
    """
    # 1. 加载原始数据
    raw_df = load_tick_data(date)
    
    # 2. 剔除停牌股
    stock_tick_counts = raw_df.groupby('stock_code').size()
    valid_stocks = stock_tick_counts[stock_tick_counts >= 100].index
    df = raw_df[raw_df['stock_code'].isin(valid_stocks)]
    
    # 3. 剔除集合竞价时段
    df = df[
        ((df['time'] >= '09:30') & (df['time'] <= '11:30')) |
        ((df['time'] >= '13:00') & (df['time'] <= '15:00'))
    ]
    
    # 4. 添加分钟索引
    df['minute_index'] = df['time'].apply(map_to_minute_index)
    
    # 5. 添加涨跌停标记
    df['limit_flag'] = df.apply(
        lambda row: detect_limit(row['price'], row['prev_close']),
        axis=1
    )
    
    # 6. 添加ST标记
    df['is_st'] = df['stock_code'].apply(is_st_stock)
    
    return df
```

---

## 4. 输出规范

**清洗后数据结构**：
| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | String | 股票代码 |
| minute_index | Int | 分钟索引（0-239） |
| price | Float64 | 成交价 |
| volume | UInt64 | 成交量 |
| amount | Float64 | 成交额 |
| bid1-5 / ask1-5 | Float64 | 五档价格 |
| bid1_vol-5_vol | UInt64 | 五档量 |
| limit_flag | Int | 涨跌停标记（1/-1/0） |
| is_st | Bool | ST标记 |

**参与计算股票条件**：
- 当日分笔记录数 ≥ 100
- 非停牌
- 非退市
