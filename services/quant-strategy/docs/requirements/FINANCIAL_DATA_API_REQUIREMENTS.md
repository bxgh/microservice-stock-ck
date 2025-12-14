# Financial Data API Requirements for Quant Strategy

**Project**: get-stockdata  
**Requester**: quant-strategy service  
**Priority**: P1 (High - Blocking EPIC-002 complete implementation)  
**Date**: 2025-12-14

---

## Business Background

The `quant-strategy` service is implementing a fundamental scoring engine (EPIC-002 Story 2.2) for long-term asset allocation. This requires comprehensive financial data to calculate quality scores across three dimensions: Profitability, Growth, and Efficiency.

**Current Status**: Story 2.1 (Risk Veto Filter) uses Mock financial data. Story 2.2 needs enhanced real financial data to provide accurate quality scoring.

---

## Required APIs

### API 1: Enhanced Financial Indicators

**Endpoint**: `GET /api/v1/finance/indicators/{stock_code}`

**Current Status**: Partially implemented in Story 2.1 with Mock data

**Required Enhancements**:

Add the following fields to the existing response:

```json
{
  "stock_code": "600519",
  "report_date": "2024-09-30",
  "report_type": "Q3",  // Q1, Q2, Q3, Annual
  
  // Income Statement (利润表) - NEW FIELDS
  "revenue": 123.45,              // 营业收入 (亿元)
  "operating_cost": 45.67,        // 营业成本 (亿元)
  "operating_profit": 67.89,      // 营业利润 (亿元)
  "net_profit": 12.0,             // 净利润 (亿元) - EXISTING
  
  // Balance Sheet (资产负债表) - NEW FIELDS
  "total_assets": 300.0,          // 总资产 (亿元) - EXISTING
  "net_assets": 150.0,            // 净资产 (亿元) - EXISTING
  "goodwill": 5.0,                // 商誉 (亿元) - EXISTING
  "monetary_funds": 30.0,         // 货币资金 (亿元) - EXISTING
  "interest_bearing_debt": 20.0,  // 有息负债 (亿元) - EXISTING
  "accounts_receivable": 15.0,    // 应收账款 (亿元) - NEW
  "inventory": 10.0,              // 存货 (亿元) - NEW
  "accounts_payable": 12.0,       // 应付账款 (亿元) - NEW
  
  // Cash Flow Statement (现金流量表) - EXISTING
  "operating_cash_flow": 15.0,    // 经营性现金流净额 (亿元) - EXISTING
  
  // Equity Structure (股权结构) - EXISTING
  "major_shareholder_pledge_ratio": 0.15  // 大股东质押率 - EXISTING
}
```

**Data Source**: 
- Tushare Pro: `fina_indicator`, `balancesheet`, `income`, `cashflow`
- AkShare: `stock_financial_abstract`

**Update Frequency**: T+1 after quarterly report release

---

### API 2: Historical Financial Data (Multi-Period)

**Endpoint**: `GET /api/v1/finance/history/{stock_code}`

**Current Status**: ❌ Does not exist - NEW API

**Purpose**: Calculate growth rates and trend analysis

**Request Parameters**:
```
?periods=8          // Number of periods to retrieve (default: 8 quarters)
?report_type=Q      // Q=Quarterly, A=Annual (default: Q)
```

**Response Format**:
```json
{
  "stock_code": "600519",
  "periods": 8,
  "report_type": "Q",
  "data": [
    {
      "report_date": "2024-09-30",
      "report_type": "Q3",
      "revenue": 123.45,
      "net_profit": 12.0,
      "total_assets": 300.0,
      "net_assets": 150.0,
      "operating_cash_flow": 15.0
      // ... all fields from API 1
    },
    {
      "report_date": "2024-06-30",
      "report_type": "Q2",
      "revenue": 115.20,
      "net_profit": 11.5,
      // ...
    }
    // ... up to 8 periods
  ]
}
```

**Use Cases**:
- Calculate YoY/QoQ growth rates
- Compute CAGR (Compound Annual Growth Rate)
- Trend analysis for scoring

**Data Source**:
- Tushare Pro: Historical queries with date ranges
- Cache strategy: Update quarterly, cache for 1 day

---

### API 3: Industry Statistics (For Normalization)

**Endpoint**: `GET /api/v1/finance/industry/{industry_code}/stats`

**Current Status**: ❌ Does not exist - NEW API

**Purpose**: Industry-relative scoring and percentile ranking

**Request Parameters**:
```
?metrics=roe,revenue_growth,asset_turnover  // Comma-separated metrics
?date=2024-09-30                            // Report date (default: latest)
```

**Response Format**:
```json
{
  "industry_code": "C39",        // CSRC/SW industry code
  "industry_name": "食品饮料",
  "stock_count": 150,
  "report_date": "2024-09-30",
  "metrics": {
    "roe": {
      "mean": 12.5,
      "median": 10.2,
      "std": 5.3,
      "p25": 8.0,      // 25th percentile
      "p50": 10.2,     // 50th percentile (median)
      "p75": 15.0,     // 75th percentile
      "p90": 20.0,     // 90th percentile
      "min": 2.0,
      "max": 35.0
    },
    "revenue_growth": {
      "mean": 15.3,
      "median": 12.1,
      // ... same structure
    },
    "asset_turnover": {
      // ...
    }
  }
}
```

**Use Cases**:
- Convert absolute scores to industry percentiles
- Identify industry leaders vs laggards
- Fair comparison across different industries

**Data Source**:
- Aggregate from all stocks in the same industry
- Update: Monthly or quarterly
- Cache: 1 day

---

## Data Quality Requirements

### Accuracy
- Financial data must match official company reports
- Validation against multiple sources when possible
- Flag suspicious data (e.g., sudden 10x changes)

### Completeness
- All required fields must be present or explicitly null
- Missing data should be clearly indicated
- Historical data should cover at least 2 years (8 quarters)

### Timeliness
- Quarterly reports: Available within T+1 after official release
- Annual reports: Available within T+1 after official release
- Industry stats: Updated monthly

### Consistency
- Use consistent units (亿元 for all monetary values)
- Use consistent date format (YYYY-MM-DD)
- Use consistent industry classification (CSRC or SW)

---

## Implementation Priority

### Phase 1 (P0 - Critical)
1. **API 1 Enhancement**: Add missing fields to existing endpoint
   - Revenue, operating cost, operating profit
   - Accounts receivable, inventory, accounts payable
   - **Timeline**: 1-2 weeks

### Phase 2 (P1 - High)
2. **API 2**: Historical financial data endpoint
   - Enable growth rate calculations
   - **Timeline**: 2-3 weeks

### Phase 3 (P2 - Medium)
3. **API 3**: Industry statistics endpoint
   - Enable industry-relative scoring
   - **Timeline**: 3-4 weeks

---

## Testing Requirements

### Unit Tests
- Validate data format and types
- Test edge cases (missing data, zero values)
- Test date range queries

### Integration Tests
- End-to-end data retrieval
- Performance testing (response time < 500ms)
- Concurrent request handling

### Data Validation
- Cross-check with official sources
- Automated data quality checks
- Anomaly detection

---

## Migration Path

### Current Workaround
`quant-strategy` is using Mock data generation for development:
- Random financial indicators based on stock code seed
- Proxy metrics for missing data
- No industry normalization

### Migration Steps
1. **API 1 Ready**: Replace Mock data with real data for existing fields
2. **API 2 Ready**: Enable real growth rate calculations
3. **API 3 Ready**: Enable industry percentile ranking

**Design**: The scoring logic is designed to be data-source agnostic, requiring only interface changes when real APIs are available.

---

## Contact & Questions

**Requester**: quant-strategy development team  
**Technical Contact**: [To be filled]  
**Business Owner**: [To be filled]

**Questions**:
1. Which data source is preferred: Tushare Pro or AkShare?
2. What is the expected SLA for data updates?
3. Are there rate limits we should be aware of?
4. Can we get a sandbox environment for testing?

---

## Appendix: Metric Calculations

### ROE (净资产收益率)
```
ROE = 净利润 / 净资产 × 100%
```

### ROIC (投入资本回报率)
```
ROIC = NOPAT / 投入资本 × 100%
其中: 投入资本 = 净资产 + 有息负债
```

### Gross Margin (毛利率)
```
毛利率 = (营业收入 - 营业成本) / 营业收入 × 100%
```

### Revenue Growth (营收增速)
```
营收增速 = (本期营收 - 上期营收) / 上期营收 × 100%
```

### Asset Turnover (资产周转率)
```
资产周转率 = 营业收入 / 总资产
```

### Days Sales Outstanding (应收账款周转天数)
```
DSO = (应收账款 / 营业收入) × 365
```

### Days Inventory Outstanding (存货周转天数)
```
DIO = (存货 / 营业成本) × 365
```

### Cash Conversion Cycle (现金转换周期)
```
CCC = DSO + DIO - DPO
```

---

*Document Version: 1.0*  
*Last Updated: 2025-12-14*  
*Status: Pending Review*
