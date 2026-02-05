# 特征工程与序列构建

## 1. 概述

对每只股票构建三个维度的**每分钟**时间序列向量：
- **向量A**：主动买入强度序列 (Active Buying Intensity)
- **向量B**：盘口失衡度序列 (Order Book Imbalance, OBI)
- **向量C**：累积收益率曲线 (Cumulative Intraday Return)

所有序列长度为 **240分钟**（上午120 + 下午120）。

---

## 2. 向量A：主动买入强度序列

### 2.1 核心目标

衡量每分钟资金的**进攻意愿**，剔除大盘股和小盘股的绝对量差异。

### 2.2 主动买卖判定

**价格位移法**：根据成交价与上一笔成交价的关系判定买卖方向。

```python
def classify_trade_direction(
    price: float, 
    last_price: float, 
    bid1: float, 
    ask1: float,
    bid1_vol: int,
    ask1_vol: int
) -> float:
    """
    判定主动买卖方向
    
    返回值：
        1.0 = 完全主动买入
        0.0 = 完全主动卖出
        0.x = 混合（价格持平时按挂单比例分配）
    """
    if price > last_price:
        # 价格上涨，判定为主动买入
        return 1.0
    elif price < last_price:
        # 价格下跌，判定为主动卖出
        return 0.0
    else:
        # 价格持平，按挂单量占比分配
        total_vol = bid1_vol + ask1_vol
        if total_vol == 0:
            return 0.5
        return bid1_vol / total_vol
```

### 2.3 涨跌停修正

```python
def apply_limit_correction(buy_ratio: float, limit_flag: int) -> float:
    """
    涨跌停修正
    
    涨停时买入需求被压缩，强制设为最大值
    跌停时卖出需求被压缩，强制设为最小值
    """
    if limit_flag == 1:  # 涨停
        return 1.0
    elif limit_flag == -1:  # 跌停
        return 0.0
    return buy_ratio
```

### 2.4 分钟级聚合

```python
def calc_minute_buying_intensity(
    minute_df: pd.DataFrame, 
    float_shares: int
) -> float:
    """
    计算单分钟主动买入强度
    
    公式：(主动买入量 - 主动卖出量) / 流通股本
    
    Args:
        minute_df: 该分钟内的所有分笔记录
        float_shares: 流通股本（股）
    
    Returns:
        归一化的主动买入强度，范围约 [-0.01, 0.01]
    """
    buy_volume = 0
    sell_volume = 0
    
    for _, row in minute_df.iterrows():
        direction = classify_trade_direction(
            row['price'], 
            row['last_price'],
            row['bid1'],
            row['ask1'],
            row['bid1_vol'],
            row['ask1_vol']
        )
        direction = apply_limit_correction(direction, row['limit_flag'])
        
        buy_volume += row['volume'] * direction
        sell_volume += row['volume'] * (1 - direction)
    
    net_buy = buy_volume - sell_volume
    return net_buy / float_shares
```

### 2.5 完整序列构建

```python
def build_vector_a(
    stock_code: str, 
    date: str, 
    tick_df: pd.DataFrame,
    float_shares: int
) -> np.ndarray:
    """
    构建主动买入强度序列（240维向量）
    """
    vector = np.zeros(240)
    
    for minute_idx in range(240):
        minute_df = tick_df[tick_df['minute_index'] == minute_idx]
        if len(minute_df) > 0:
            vector[minute_idx] = calc_minute_buying_intensity(
                minute_df, float_shares
            )
    
    return vector
```

---

## 3. 向量B：盘口失衡度序列 (OBI)

### 3.1 核心目标

描述每分钟盘口的**挂单意图**：主力是在"挂单护盘"还是在"挂单压货"。

### 3.2 加权OBI公式

$$OBI = \frac{\sum_{i=1}^{5} w_i \times (Bid_i - Ask_i)}{\sum_{i=1}^{5} w_i \times (Bid_i + Ask_i)}$$

其中权重采用**线性衰减**：$w_i = \frac{6-i}{15}$

| 档位 | 权重 |
|------|------|
| 1档 | 5/15 = 0.333 |
| 2档 | 4/15 = 0.267 |
| 3档 | 3/15 = 0.200 |
| 4档 | 2/15 = 0.133 |
| 5档 | 1/15 = 0.067 |

### 3.3 计算实现

```python
def calc_obi(
    bid_vols: list[int],  # [bid1_vol, bid2_vol, ..., bid5_vol]
    ask_vols: list[int]   # [ask1_vol, ask2_vol, ..., ask5_vol]
) -> float:
    """
    计算单个快照的加权OBI
    
    返回值范围：[-1, 1]
    - 正值表示买盘挂单强于卖盘（护盘）
    - 负值表示卖盘挂单强于买盘（压货）
    """
    weights = [5/15, 4/15, 3/15, 2/15, 1/15]
    
    numerator = 0.0
    denominator = 0.0
    
    for i in range(5):
        bid = bid_vols[i]
        ask = ask_vols[i]
        w = weights[i]
        
        numerator += w * (bid - ask)
        denominator += w * (bid + ask)
    
    if denominator == 0:
        return 0.0
    
    return numerator / denominator
```

### 3.4 分钟级聚合

```python
def build_vector_b(
    stock_code: str, 
    date: str, 
    orderbook_df: pd.DataFrame
) -> np.ndarray:
    """
    构建盘口失衡度序列（240维向量）
    
    取每分钟内所有快照OBI的均值
    """
    vector = np.zeros(240)
    
    for minute_idx in range(240):
        minute_df = orderbook_df[orderbook_df['minute_index'] == minute_idx]
        if len(minute_df) > 0:
            obi_values = []
            for _, row in minute_df.iterrows():
                bid_vols = [row[f'bid{i}_vol'] for i in range(1, 6)]
                ask_vols = [row[f'ask{i}_vol'] for i in range(1, 6)]
                obi_values.append(calc_obi(bid_vols, ask_vols))
            vector[minute_idx] = np.mean(obi_values)
    
    return vector
```

---

## 4. 向量C：累积收益率曲线

### 4.1 核心目标

描述日内价格走势形态，用于验证向量A/B的有效性。

### 4.2 计算公式

$$C_t = \frac{Price_t - PrevClose}{PrevClose}$$

### 4.3 实现

```python
def build_vector_c(
    stock_code: str, 
    date: str, 
    tick_df: pd.DataFrame,
    prev_close: float
) -> np.ndarray:
    """
    构建累积收益率曲线（240维向量）
    
    取每分钟收盘价（最后一笔成交价）
    """
    vector = np.zeros(240)
    
    for minute_idx in range(240):
        minute_df = tick_df[tick_df['minute_index'] == minute_idx]
        if len(minute_df) > 0:
            minute_close = minute_df.iloc[-1]['price']
            vector[minute_idx] = (minute_close - prev_close) / prev_close
        elif minute_idx > 0:
            # 无成交时延续上一分钟
            vector[minute_idx] = vector[minute_idx - 1]
    
    return vector
```

---

## 5. 新增特征

### 5.1 相对成交量序列 (RVS)

捕捉"放量"信号。

```python
def build_rvs(
    stock_code: str, 
    date: str, 
    tick_df: pd.DataFrame,
    avg_minute_volume: float  # 过去N日分钟均量
) -> np.ndarray:
    """
    构建相对成交量序列
    
    RVS_t = 当前分钟成交量 / 过去N日分钟均量
    """
    vector = np.zeros(240)
    
    for minute_idx in range(240):
        minute_df = tick_df[tick_df['minute_index'] == minute_idx]
        minute_volume = minute_df['volume'].sum() if len(minute_df) > 0 else 0
        vector[minute_idx] = minute_volume / avg_minute_volume if avg_minute_volume > 0 else 0
    
    return vector
```

### 5.2 大单占比序列

识别主力资金痕迹。

```python
def build_large_order_ratio(
    stock_code: str, 
    date: str, 
    tick_df: pd.DataFrame,
    large_threshold: float = 100000  # 大单阈值（元）
) -> np.ndarray:
    """
    构建大单占比序列
    
    大单定义：单笔成交额 > 阈值
    """
    vector = np.zeros(240)
    
    for minute_idx in range(240):
        minute_df = tick_df[tick_df['minute_index'] == minute_idx]
        if len(minute_df) > 0:
            total_amount = minute_df['amount'].sum()
            large_amount = minute_df[minute_df['amount'] > large_threshold]['amount'].sum()
            vector[minute_idx] = large_amount / total_amount if total_amount > 0 else 0
    
    return vector
```

### 5.3 集合竞价特征向量

```python
def build_auction_vector(
    stock_code: str, 
    date: str, 
    tick_df: pd.DataFrame,
    prev_close: float
) -> dict:
    """
    构建集合竞价特征（非时序，作为补充标签）
    """
    open_auction = tick_df[
        (tick_df['time'] >= '09:15') & (tick_df['time'] < '09:25')
    ]
    close_auction = tick_df[
        (tick_df['time'] >= '14:57') & (tick_df['time'] <= '15:00')
    ]
    
    return {
        # 开盘集合竞价
        'open_auction_volume_ratio': open_auction['volume'].sum() / tick_df['volume'].sum(),
        'open_gap': (tick_df[tick_df['minute_index'] == 0].iloc[0]['price'] - prev_close) / prev_close,
        
        # 尾盘集合竞价
        'close_auction_volume_ratio': close_auction['volume'].sum() / tick_df['volume'].sum(),
        'close_rush': close_auction['price'].iloc[-1] - close_auction['price'].iloc[0] if len(close_auction) > 1 else 0,
    }
```

---

## 6. 输出规范

### 5.4 完整特征矩阵 (9-Column Matrix)

特征管线（`StrategyFactory`）最终输出深度为 240 分钟、宽度为 9 维的标准化特征矩阵。

| 索引 | 特征名 | 维度 | 范围 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| **0** | **vector_a** | 240 | [-0.01, 0.01] | 主动买入强度 (Basic) |
| **1** | **vector_b** | 240 | [-1, 1] | 盘口失衡度 (OBI) |
| **2** | **vector_c** | 240 | [-0.2, 0.2] | 分时累积收益率 |
| **3** | **LOR** | 240 | [0, 1] | 大单成交占比 (TradeSize) |
| **4** | **NLB** | 240 | (-inf, +inf) | 大单净买入额 (元) |
| **5** | **NLB_Ratio** | 240 | [-1, 1] | 归一化大单净买入强度 |
| **6** | **RID** | 240 | {-2, 0, 2} | 机构/散户背离度 |
| **7** | **VPIN** | 240 | [0, 1] | 知情交易概率 (Liquidity) |
| **8** | **Lambda** | 240 | [0, +inf) | 价格冲击系数 (Kyle's $\lambda$) |

---

## 6. 存储规范 (Persistence)

特征计算完成后，以 `(240, 9)` 的矩阵形式序列化并存入 **Redis FeatureStore**。
- **Key 格式**: `feature:v1:{stock_code}:{date}`
- **TTL**: 7 天
- **性能**: 百只股票加载耗时 < 50ms。

## 7. 参数配置

```yaml
feature_engineering:
  # 主动买入强度
  vector_a:
    use_limit_correction: true
  
  # 盘口失衡度
  vector_b:
    weight_decay: "linear"  # linear / exponential / uniform
    levels: 5
  
  # 相对成交量
  rvs:
    lookback_days: 20
  
  # 大单阈值
  large_order:
    threshold_amount: 100000  # 元
```
