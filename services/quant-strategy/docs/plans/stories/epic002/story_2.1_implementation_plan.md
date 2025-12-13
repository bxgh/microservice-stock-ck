# Story 2.1 Implementation Plan: 风险否决过滤器

## 1. 目标描述
**Story**: 2.1 Risk Veto Filter  
**Goal**: 实现基于财务指标的"一票否决"机制，在进入核心股票池之前，自动剔除存在重大财务风险或合规风险的标的。  
**Rationale**: "避坑"比"踩对"更重要。通过量化手段自动识别高风险特征（如高商誉、高质押、存贷双高等），保护长线投资本金安全。

## 2. 核心组件设计

### 2.1 财务数据适配 (Data Layer)
需要扩展 `StockDataProvider` 以获取高级财务指标。
*   **API Endpoint**: 假设 `get-stockdata` 提供了 `/api/v1/finance/indicators/{code}` 接口（如无，需 Mock 或请求开发）。
*   **Data Model**: `FinancialIndicators` (包含商誉、净资产、质押率、经营现金流、净利润等)。

### 2.2 风控规则实现 (Domain Layer)
基于 Story 1.7 建立的 `RiskRule` 基类，实现以下具体规则：

1.  **`GoodwillRiskRule` (商誉风控)**
    *   逻辑: 商誉 / 净资产 >阈值 (默认 30%) -> 拒绝。
    *   原因: 高商誉意味着巨大的减值雷。

2.  **`PledgeRiskRule` (质押风控)**
    *   逻辑: 大股东质押比例 >阈值 (默认 50%) -> 拒绝。
    *   原因: 高质押面临爆仓和控制权变更风险。

3.  **`CashflowQualityRule` (收现比风控)**
    *   逻辑: (经营性现金流净额 / 净利润) <阈值 (默认 0.5) 且 净利润 > 0 -> 拒绝。
    *   原因: 利润是纸面的，现金流才是真实的。

4.  **`FinancialFraudRule` (存贷双高)**
    *   逻辑: (货币资金 / 总资产 > 20%) AND (有息负债 / 总资产 > 20%) -> 警告/拒绝。
    *   原因: 账上有钱却借很多钱，典型造假特征。

### 2.3 集成 (Service Layer)
*   **`FundamentalFilter`**: 一个新的服务类，封装 `RiskManager`，专门用于长线选股的批量过滤。
*   或直接扩充 `RiskManager` 的默认规则集（但长线规则通常不用于日内高频交易，建议分离配置）。

## 3. 详细变更 (Proposed Changes)

### 3.1 [NEW] `src/adapters/finance_data.py`
定义财务数据模型和获取逻辑。

```python
class FinancialIndicators(BaseModel):
    goodwill: float         # 商誉
    net_assets: float       # 净资产
    major_shareholder_pledge_ratio: float # 大股东质押率
    operating_cash_flow: float # 经营现金流
    net_profit: float       # 净利润
    monetary_funds: float   # 货币资金
    interest_bearing_debt: float # 有息负债
    total_assets: float     # 总资产
```

### 3.2 [NEW] `src/strategies/rules_fundamental.py`
实现上述 4 个具体的 `RiskRule` 子类。

### 3.3 [MODIFY] `src/adapters/stock_data_provider.py`
添加 `get_financial_indicators(code)` 方法。

## 4. 验证计划

### 4.1 单元测试
*   构造虚假的财务数据（如商誉占比 50%），验证规则是否返回 `False`。
*   构造健康数据，验证规则返回 `True`。

### 4.2 集成测试
*   这也是验证 `RiskManager` 扩展性的好机会。
*   验证从 DataProvider -> Rule -> Result 的完整链路。

## User Review Required
> [!IMPORTANT]
> **数据依赖**: 目前 `get-stockdata` 可能尚未提供详细的财务指标接口。
> **方案**: 
> 1. 如果接口不存在，先在 DataProvider 中实现 Mock 数据生成。
> 2. 向数据团队提需求 (Blocker)。
> **本 Story 将优先使用 Mock 数据完成逻辑开发。**
