# 分钟级非流动性指标 (Minute ILLIQ)

> **优先级**: P3 - 低优先
> **理论来源**: Amihud (2002) 非流动性指标的分钟级变体

## 1. 核心假设

**假设**: 异常的"成交量-价格变动比"预示主力行为或流动性异常。

| 场景 | ILLIQ值 | 可能含义 |
|------|---------|----------|
| 放量不涨 | 极低 | 主力吸筹，压制价格 |
| 缩量大涨 | 极高 | 流动性真空/人为操纵 |
| 放量大涨 | 中等 | 正常趋势 |

---

## 2. 理论背景

### 2.1 Amihud ILLIQ (原版)

Amihud (2002) 定义的日度非流动性指标：

$$ILLIQ_{daily} = \frac{|R_{daily}|}{Volume_{daily}}$$

**含义**: 单位成交量导致的价格变动。

### 2.2 本方案改进

将日度指标改为**分钟级**：

$$ILLIQ_t = \frac{|R_t^{minute}|}{Volume_t^{minute}}$$

**优势**:
- 更高频率捕捉异常
- 可实时监控
- 适配分笔数据

---

## 3. 计算方法

### 3.1 分钟级收益率

$$R_t = \frac{P_t^{close} - P_t^{open}}{P_t^{open}}$$

其中：
- $P_t^{open}$：该分钟第一笔成交价
- $P_t^{close}$：该分钟最后一笔成交价

### 3.2 分钟级ILLIQ

$$ILLIQ_t = \frac{|R_t|}{Volume_t + 1}$$

加1避免除零。

### 3.3 归一化

为跨股票可比，进行归一化：

$$ILLIQ_{norm,t} = \frac{ILLIQ_t}{\overline{ILLIQ}_{20day}}$$

使用过去20日同时段均值归一化。

---

## 4. 信号解读

### 4.1 ILLIQ异常低

**条件**: ILLIQ_norm < 0.3

**可能含义**:
- 大量成交但价格稳定
- 主力吸筹，对手盘充足
- 或大宗交易冲击

**操作建议**: 关注后续走势，可能酝酿行情

### 4.2 ILLIQ异常高

**条件**: ILLIQ_norm > 3.0

**可能含义**:
- 少量成交导致大幅波动
- 流动性真空
- 或人为操纵价格

**操作建议**: 避免交易，滑点风险高

---

## 5. 与原框架集成

### 5.1 作为流动性过滤器

与Kyle's Lambda和VPIN形成流动性监控三角：

| 指标 | 维度 | 配合使用 |
|------|------|----------|
| VPIN | 知情交易 | 信息冲击预警 |
| λ | 价格敏感度 | 冲击成本评估 |
| ILLIQ | 量价关系 | 异常行为检测 |

### 5.2 主力行为检测

结合其他指标：
- ILLIQ低 + 大单占比高 → 主力吸筹
- ILLIQ低 + OBI动量正 → 护盘吸货
- ILLIQ高 + 成交清淡 → 无人问津

---

## 6. 新增特征：ILLIQ序列

### 6.1 构建向量

对每只股票构建240分钟ILLIQ向量：

$$ILLIQ\_Vector = [ILLIQ_0, ILLIQ_1, ..., ILLIQ_{239}]$$

### 6.2 DTW融合（可选）

作为第四个特征序列参与相似度计算：

$$D_{total} = \alpha \times DTW(A) + \beta \times DTW(B) + \gamma \times DTW(C) + \epsilon \times DTW(ILLIQ)$$

---

## 7. Level-1数据适配

### 7.1 数据需求

| 字段 | 必需性 | Level-1可用性 |
|------|--------|---------------|
| 成交价 | ✅ 必需 | ✅ 可用 |
| 成交量 | ✅ 必需 | ✅ 可用 |

### 7.2 注意事项

- 无成交的分钟，ILLIQ无法计算，设为NaN或上一分钟值
- 开盘前几分钟成交波动大，ILLIQ不稳定

---

## 8. 回测验证要点

### 8.1 验证假设

1. ILLIQ异常低的分钟，后续5分钟是否更易上涨？
2. ILLIQ异常高时入场，滑点是否显著增加？
3. ILLIQ与大单占比的相关性如何？

### 8.2 分层分析

| ILLIQ区间 | 样本 | 观察指标 |
|-----------|------|----------|
| < P10 | 极低 | 后续收益、主力行为占比 |
| P10-P90 | 正常 | 基准 |
| > P90 | 极高 | 滑点、波动率 |

---

## 9. 参数配置

```yaml
minute_illiq:
  # 计算参数
  calculation:
    volume_offset: 1  # 避免除零
    
  # 归一化
  normalization:
    lookback_days: 20
    
  # 异常阈值
  thresholds:
    low: 0.3      # 归一化后低于0.3
    high: 3.0     # 归一化后高于3.0
    
  # DTW融合
  dtw:
    enabled: false  # 默认不参与DTW
    weight: 0.1
```

---

## 10. 参考文献

1. **Amihud, Y.** (2002). Illiquidity and Stock Returns: Cross-Section and Time-Series Effects. *Journal of Financial Markets*.

2. **Goyenko, R. Y., Holden, C. W., & Trzcinka, C. A.** (2009). Do Liquidity Measures Measure Liquidity? *Journal of Financial Economics*.

3. **Lesmond, D. A.** (2005). Liquidity of Emerging Markets. *Journal of Financial Economics*.
