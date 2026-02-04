# VPIN - 成交量同步知情交易概率

> **优先级**: P1 - 高优先
> **理论来源**: Maureen O'Hara & David Easley (Cornell University)

## 1. 核心假设

**假设**: 知情交易者的活跃度可通过成交量失衡检测，VPIN极端值预示流动性危机。

**实证支持**:
- 2010年5月6日美股"闪崩"前1小时，VPIN发出高毒性预警
- 高VPIN → 做市商撤退 → 流动性枯竭 → 价格崩溃

---

## 2. 理论背景

### 2.1 PIN vs VPIN

| 模型 | PIN (原版) | VPIN (改进版) |
|------|-----------|---------------|
| 时间基准 | 日历时间 | 成交量时钟 |
| 更新频率 | 每日 | 实时（每个成交量桶） |
| 适用场景 | 日频分析 | 高频/日内分析 |
| 计算复杂度 | 需MLE估计 | 简单公式 |

### 2.2 成交量时钟

核心思想：信息事件按**成交量**到达，而非按时间到达。

- 活跃时段：成交量大，信息密集
- 平静时段：成交量小，信息稀疏

因此用"成交量桶"替代"时间窗口"更能捕捉信息节奏。

---

## 3. 计算方法

### 3.1 成交量分桶

将全天成交量按固定大小分割为N个"桶"：

$$\text{桶大小} = \frac{\text{预估日成交量}}{N}$$

**推荐参数**:
- N = 50（每天50个桶）
- 对于日均成交1亿股的股票，每桶200万股

### 3.2 买卖失衡计算

对每个桶，计算买卖失衡：

$$V_{buy}^{(i)} = \sum_{t \in bucket_i} V_t \times P(buy | \Delta P_t)$$
$$V_{sell}^{(i)} = \sum_{t \in bucket_i} V_t \times P(sell | \Delta P_t)$$

简化方法（基于价格变动）：
- 价格上涨 → 全部计为买入
- 价格下跌 → 全部计为卖出
- 价格持平 → 按50/50分配

### 3.3 VPIN公式

$$VPIN = \frac{\sum_{i=1}^{N} |V_{buy}^{(i)} - V_{sell}^{(i)}|}{\sum_{i=1}^{N} (V_{buy}^{(i)} + V_{sell}^{(i)})}$$

**取值范围**: [0, 1]
- VPIN ≈ 0：买卖平衡，流动性充足
- VPIN ≈ 1：极端失衡，流动性枯竭

---

## 4. 信号解读

### 4.1 阈值设定

| VPIN区间 | 市场状态 | 操作建议 |
|----------|----------|----------|
| < 0.3 | 正常 | 无需干预 |
| 0.3 - 0.5 | 警戒 | 关注 |
| 0.5 - 0.7 | 危险 | 减仓 |
| > 0.7 | 极度危险 | 清仓/对冲 |

### 4.2 VPIN突变信号

**计算VPIN变化率**：

$$\Delta VPIN = VPIN_{current} - VPIN_{prev\_bucket}$$

- ΔVpin > 0.1 → 流动性快速恶化
- ΔVpin < -0.1 → 流动性快速恢复

---

## 5. 与原框架集成

### 5.1 作为风控过滤器

在Cluster信号生成前，检查VPIN：

```
if VPIN > 0.5:
    skip_cluster_signals()  # 暂停生成交易信号
    emit_risk_warning()     # 发出风险预警
```

### 5.2 作为Cluster质量指标

低VPIN的Cluster更可信：
- VPIN < 0.3 的Cluster：流动性充足，信号可执行
- VPIN > 0.5 的Cluster：流动性不足，慎重操作

---

## 6. Level-1数据适配

### 6.1 数据需求

| 字段 | 必需性 | Level-1可用性 |
|------|--------|---------------|
| 成交量 | ✅ 必需 | ✅ 可用 |
| 成交价 | ✅ 必需 | ✅ 可用 |
| 买卖方向 | ⚠️ 需推断 | 用价格变动推断 |

### 6.2 3秒快照处理

Level-1的3秒快照可能包含多笔交易：
- 直接使用快照内的总成交量
- 按快照间价格变动判定整体方向

---

## 7. 回测验证要点

### 7.1 验证假设

1. VPIN > 0.5 后的5分钟，价格波动是否放大？
2. VPIN极端值出现后，日内最大回撤是否增加？
3. 相同Cluster策略在高VPIN时的胜率是否下降？

### 7.2 基准对比

| 策略 | 描述 | 预期 |
|------|------|------|
| 无过滤 | 忽略VPIN | 基准 |
| VPIN过滤 | VPIN>0.5时不交易 | 降低回撤 |
| VPIN加权 | 低VPIN时增加仓位 | 提高收益 |

---

## 8. 参数配置

```yaml
vpin:
  # 分桶参数
  buckets:
    n_buckets: 50  # 每天桶数
    
  # 阈值
  thresholds:
    normal: 0.3
    warning: 0.5
    danger: 0.7
    
  # 滚动窗口
  rolling:
    window_buckets: 10  # 计算VPIN使用的历史桶数
```

---

## 9. 参考文献

1. **Easley, D., López de Prado, M. M., & O'Hara, M.** (2012). Flow Toxicity and Liquidity in a High-frequency World. *Review of Financial Studies*.

2. **Easley, D., López de Prado, M. M., & O'Hara, M.** (2011). The Microstructure of the "Flash Crash". *Journal of Portfolio Management*.

3. **Andersen, T. G., & Bondarenko, O.** (2014). VPIN and the Flash Crash. *Journal of Financial Markets*.
