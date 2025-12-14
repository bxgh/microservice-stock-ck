# EPIC-002 Data APIs Documentation

## Overview
This document details the new financial, market valuation, and industry comparison APIs implemented for the **Long-term Asset Allocation System** (EPIC-002).

**Base URL**: `/api/v1`

## 1. Core Financial Data (`FinanceRouter`)

Provides access to detailed financial statements and indicators.

### 1.1 Enhanced Indicators
`GET /finance/indicators/{stock_code}`

Returns enhanced financial indicators including revenue, profit, cash flow, and debt metrics.

**Parameters:**
- `stock_code` (path): Stock code (e.g., "600519")

**Response:**
```json
{
  "stock_code": "600519",
  "report_date": "2024-03-31",
  "report_type": "Q1",
  "revenue": 457.76,            // 亿元
  "net_profit": 240.65,         // 亿元
  "operating_cash_flow": 91.89, // 亿元
  "total_assets": 2736.94       // 亿元
  // ... other fields
}
```

### 1.2 Financial History
`GET /finance/history/{stock_code}`

Returns historical financial data for trend analysis.

**Parameters:**
- `stock_code` (path): Stock code
- `periods` (query): Number of periods to retrieve (default: 8)
- `report_type` (query): "Q" (Quarterly) or "A" (Annual) (default: "Q")

**Response:**
```json
{
  "stock_code": "600519",
  "periods": 8,
  "report_type": "Q",
  "data": [
    { "report_date": "2024-03-31", "revenue": 457.76, ... },
    { "report_date": "2023-12-31", "revenue": 1476.94, ... }
  ]
}
```

---

## 2. Market Valuation (`ValuationRouter`)

Provides real-time and historical valuation metrics.

### 2.1 Current Valuation
`GET /market/valuation/{stock_code}`

Returns real-time valuation ratios.

**Parameters:**
- `stock_code` (path): Stock code

**Response:**
```json
{
  "stock_code": "600519",
  "report_date": "2024-05-20",
  "pe_ttm": 24.5,
  "pb_ratio": 8.2,
  "dividend_yield_ttm": 2.8,
  "total_market_cap": 21000.5 // 亿元
}
```

### 2.2 Historical Valuation
`GET /market/valuation/{stock_code}/history`

Returns historical PE/PB series and statistical distribution.

**Parameters:**
- `stock_code` (path): Stock code
- `years` (query): History length in years (default: 5)
- `frequency` (query): Data frequency (D/W/M) (default: "D")

**Response:**
```json
{
  "stock_code": "600519",
  "years": 5,
  "stats": {
    "pe_ttm": {
      "mean": 35.2,
      "median": 32.1,
      "p25": 28.5,
      "p75": 40.2
    }
  },
  "dates": ["2019-01-01", ...],
  "pe_ttm_list": [28.5, 29.1, ...],
  "pb_ratio_list": [8.1, 8.2, ...]
}
```

---

## 3. Industry Comparison (`IndustryRouter`)

Provides industry classification and aggregated statistics.

### 3.1 Industry Statistics
`GET /finance/industry/{industry_code}/stats`

Returns aggregated valuation and performance statistics for an industry.

**Parameters:**
- `industry_code` (path): Industry name or code (e.g., "酿酒行业")

**Response:**
```json
{
  "industry_name": "酿酒行业",
  "stock_count": 38,
  "report_date": "2024-05-20",
  "pe_ttm_stats": {
    "mean": 28.5,
    "median": 24.1,
    "p25": 18.2,
    "p75": 35.6
  },
  "pb_ratio_stats": {
    "mean": 4.2,
    "median": 3.5
  }
}
```

### 3.2 Enhanced Stock Info (Updated)
`GET /stocks/{stock_code}/detail`

The stock detail endpoint now includes industry classification.

**Response Update:**
```json
{
  "data": {
    "stock_code": "600519",
    "stock_name": "贵州茅台",
    "industry": "酿酒行业",
    "sector": "主板"
    // ... existing fields
  }
}
```
