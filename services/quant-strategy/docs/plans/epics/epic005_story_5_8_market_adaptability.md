### Story 5.8: 市场环境适应性机制 (Phase 2)
**工期**: 1 天  
**优先级**: P2 (Phase 2 增强功能)

**目标**: 根据市场环境动态调整股票池规模和筛选标准。

> [!WARNING]
> **实施阶段**: Phase 2  
> 此功能复杂度较高，建议在基础池管理稳定运行后（约 1 个月）再实施。

**核心功能**:
1. **市场情绪指标**:
   - VIX 指数（波动率）
   - 涨跌比（上涨/下跌股票数量）
   - 成交量比率（相对历史平均）

2. **动态池规模调整**:
```python
def calculate_pool_sizes(market_sentiment_score):
    base_sizes = {\"long_candidate\": 300, \"swing_candidate\": 150}
    
    if market_sentiment_score > 0.7:  # 强势市场
        multiplier = 1.3
    elif market_sentiment_score < 0.3:  # 弱势市场
        multiplier = 0.7
    else:
        multiplier = 1.0
    
    return {pool: int(size *

 multiplier) for pool, size in base_sizes.items()}
```

3. **极端行情应对**:
   - 市场暴跌 (指数单日跌幅 >5%): 暂停开仓、减仓30%
   - VIX 飙升 (>历史均值1.5倍): 提高现金比例至20%

**验收标准**:
- [ ] 实现VIX、涨跌比等市场情绪指标计算
- [ ] 池规模可根据市场环境自动调整（±30%）
- [ ] 极端行情下自动触发风控措施
- [ ] 提供市场环境仪表盘

---

