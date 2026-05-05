# Epic 2: 核心指标引擎 (CSD 信号)

## 目标
实现临界慢化（Critical Slowing Down）理论下的四种核心预警信号，并合成 CCI 指数。

## Stories (实施顺序)

### Story 2.1: 横截面相关性 (ρ̄) 基石实现 ⭐⭐⭐
**Priority: P0**
- **背景**：ρ̄ 是整个项目的数学基石，所有 CCI 计算都依赖它。
- **技术实现**：在 `src/signals/correlation.py` 中使用 NumPy 矢量化实现高性能计算。
- **性能要求**：300 股 × 250 天数据计算耗时 < 3s。

### Story 2.2: 辅助三信号 (方差/自相关/偏度)
**Priority: P1**
- **实现**：`src/signals/variance.py`, `src/signals/autocorr.py`, `src/signals/skewness.py`。
- **逻辑**：检测系统恢复变慢（方差上升）、可预测性上升（AR1）和分布失衡（偏度）。

### Story 2.3: CCI 指数合成逻辑
- **实现**：根据权重 `alpha, beta, gamma, delta` 合成 0-2 范围的 CCI 值。
- **验收**：输入标准测试数据，输出预期的 CCI 序列。

### Story 2.4: 信号引擎单元测试集
- **要求**：覆盖所有信号的边界情况（数据不足、全 0 收益率、NaN 处理）。
