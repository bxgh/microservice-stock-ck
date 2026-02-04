# OBI动量 - 盘口失衡变化率

> **优先级**: P2 - 中优先
> **理论来源**: 原方案OBI的增强版，结合动量分析

## 1. 核心假设

**假设**: 盘口失衡的**变化速度**比绝对值更有预测力。

**原方案问题**:
- 仅计算OBI绝对值
- 静态快照，忽略动态趋势
- 无法区分"稳定护盘"与"加速撤单"

**改进方向**:
- OBI绝对值 → OBI变化率
- 单点观测 → 趋势判断

---

## 2. OBI回顾

### 2.1 原OBI公式

$$OBI = \frac{\sum_{i=1}^{5} w_i \times (Bid_i - Ask_i)}{\sum_{i=1}^{5} w_i \times (Bid_i + Ask_i)}$$

**取值范围**: [-1, 1]
- OBI > 0：买盘挂单强于卖盘
- OBI < 0：卖盘挂单强于买盘

### 2.2 局限性

| 场景 | OBI绝对值 | 实际含义 | 问题 |
|------|----------|----------|------|
| OBI=0.5稳定 | 高 | 长期护盘 | 无法区分 |
| OBI从0.8→0.5 | 中 | 买盘撤单中 | 无法区分 |
| OBI从0.2→0.5 | 中 | 买盘加码中 | 无法区分 |

---

## 3. OBI动量定义

### 3.1 一阶动量（变化率）

$$OBI\_Momentum_t = OBI_t - OBI_{t-1}$$

**信号含义**:
- 正值 → 买盘加速堆积
- 负值 → 卖盘加速堆积（或买盘撤单）

### 3.2 平滑动量

使用滚动均值平滑噪音：

$$\overline{OBI\_Mom}_t = \frac{1}{k}\sum_{i=0}^{k-1} OBI\_Momentum_{t-i}$$

推荐k=5（5分钟平滑）

### 3.3 二阶动量（加速度）

$$OBI\_Accel_t = OBI\_Momentum_t - OBI\_Momentum_{t-1}$$

**信号含义**:
- 正值 → 堆积速度加快
- 负值 → 堆积速度减慢

---

## 4. 信号解读

### 4.1 四象限模型

| OBI绝对值 | OBI动量 | 状态 | 信号 |
|-----------|---------|------|------|
| 高(>0.3) | 正 | 强势加速 | 强买入 |
| 高(>0.3) | 负 | 强势衰减 | 警惕反转 |
| 低(<-0.3) | 正 | 弱势修复 | 观望 |
| 低(<-0.3) | 负 | 弱势加剧 | 强卖出 |

### 4.2 背离信号

**价格-OBI动量背离**:
- 价格上涨 + OBI动量负 → 假突破，回调概率高
- 价格下跌 + OBI动量正 → 超卖反弹机会

---

## 5. 与原框架集成

### 5.1 替换原向量B

原向量B（OBI序列）可增强为：
- **向量B'**: OBI动量序列
- 或保留B，新增B'作为补充特征

### 5.2 DTW多维扩展

原方案融合向量A、B、C，可扩展为：

$$D_{total} = \alpha \times DTW(A) + \beta \times DTW(B) + \gamma \times DTW(C) + \delta \times DTW(B')$$

推荐权重：α=0.4, β=0.2, γ=0.2, δ=0.2

### 5.3 分歧度增强

原方案分歧度仅基于收益率，可增加：
- OBI动量分歧度：Cluster内OBI动量方向一致性
- 分歧 = OBI动量方向不一致的股票占比

---

## 6. 信号生成

### 6.1 买入信号

**条件**:
- OBI > 0.2（买盘占优）
- OBI动量 > 0（买盘加速）
- OBI加速度 > 0（速度还在增加）
- 持续3分钟以上

### 6.2 卖出信号

**条件**:
- OBI动量由正转负
- 持续2分钟以上
- 价格未明显下跌（主力开始撤单）

### 6.3 假突破预警

**条件**:
- 价格创日内新高
- OBI动量 < 0（买盘在减少）
- 成交量未放大

---

## 7. Level-1数据适配

### 7.1 数据需求

| 字段 | 必需性 | Level-1可用性 |
|------|--------|---------------|
| 五档买价 | ✅ 必需 | ✅ 可用 |
| 五档买量 | ✅ 必需 | ✅ 可用 |
| 五档卖价 | ✅ 必需 | ✅ 可用 |
| 五档卖量 | ✅ 必需 | ✅ 可用 |

### 7.2 采样频率

Level-1五档数据每3秒更新一次，需注意：
- 分钟级OBI取3秒快照的均值
- OBI动量在分钟级计算，避免噪音

---

## 8. 回测验证要点

### 8.1 验证假设

1. OBI动量为正时，后续5分钟涨幅是否更高？
2. 价格-OBI动量背离后，反转概率是否显著？
3. 使用OBI动量的DTW聚类效果是否优于原OBI？

### 8.2 对比实验

| 策略 | 特征 | 预期 |
|------|------|------|
| 原向量B | OBI绝对值 | 基准 |
| 向量B' | OBI动量 | 更优 |
| B+B'融合 | 两者结合 | 最优 |

---

## 9. 参数配置

```yaml
obi_momentum:
  # 基础OBI
  obi:
    weight_decay: "linear"  # 线性衰减权重
    levels: 5
    
  # 动量计算
  momentum:
    diff_periods: 1         # 一阶差分
    smooth_window: 5        # 平滑窗口（分钟）
    
  # 信号阈值
  signals:
    min_obi: 0.2
    min_momentum: 0.05
    min_duration: 3         # 最小持续分钟数
    
  # DTW融合权重
  dtw_weight: 0.2
```

---

## 10. 参考文献

1. **Cao, C., Hansch, O., & Wang, X.** (2009). The Information Content of an Open Limit-Order Book. *Journal of Futures Markets*.

2. **Biais, B., Hillion, P., & Spatt, C.** (1995). An Empirical Analysis of the Limit Order Book and the Order Flow in the Paris Bourse. *Journal of Finance*.

3. **Cont, R., Kukanov, A., & Stoikov, S.** (2014). The Price Impact of Order Book Events. *Journal of Financial Econometrics*.
