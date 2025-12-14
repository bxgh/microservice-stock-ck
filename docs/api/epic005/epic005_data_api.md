# EPIC-005 Data API Reference

This document details the data APIs implemented for EPIC-005 (Multi-Level Stock Pool Support). These APIs provide real-time quotes, liquidity metrics, and stock status information required for the `quant-strategy` service.

## Base URL
`http://localhost:8001/api/v1`

---

## 1. Batch Real-time Quotes
**Endpoint**: `GET /quotes/realtime`

Fetch real-time snapshot data for a batch of stocks. Optimized for high-frequency polling.

**Parameters**:
- `codes` (query, required): Comma-separated list of stock codes (e.g., `600519,000001`).

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "code": "600519",
      "name": "贵州茅台",
      "price": 1750.50,
      "change_pct": 1.25,
      "volume": 45000,
      "turnover": 78000000.0,
      "turnover_ratio": 0.5,
      "market_cap": 2200000000000.0,
      "timestamp": "2025-12-14T10:00:00.123456"
    }
  ],
  "count": 1
}
```

---

## 2. Stock Liquidity Metrics
**Endpoint**: `GET /stocks/{stock_code}/liquidity`

Get liquidity analysis data including 20-day average volume, bid-ask spread, and order book depth.

**Parameters**:
- `stock_code` (path, required): Stock code (e.g., `600519`).

**Response**:
```json
{
  "success": true,
  "data": {
    "stock_code": "600519",
    "avg_daily_volume": 55000.0,    // 20-day average volume
    "avg_turnover_20d": 95000000.0, // 20-day average turnover
    "bid_ask_spread": 0.15,         // Current spread (Ask1 - Bid1)
    "liquidity_score": 85.0,        // derived score (0-100)
    "order_book_depth_5": {
      "bids": [
        {"price": 1750.0, "volume": 100},
        {"price": 1749.9, "volume": 200}
      ],
      "asks": [
        {"price": 1750.15, "volume": 50},
        {"price": 1750.20, "volume": 100}
      ],
      "timestamp": "2025-12-14T10:00:00.123456",
      "simulated": false // true if L1 data unavailable and simulated
    }
  }
}
```

---

## 3. Stock Status Check
**Endpoint**: `GET /stocks/{stock_code}/status`

Check special warnings or trading status (ST, Suspension, Delisting).

**Parameters**:
- `stock_code` (path, required): Stock code.

**Response**:
```json
{
  "stock_code": "600519",
  "name": "贵州茅台",
  "is_st": false,         // True if Special Treatment (ST/*ST)
  "is_suspended": false,  // True if currently halted/suspended
  "is_delisted": false,   // True if in delisting period
  "trading_status": "TRADING" // TRADING, HALT, DELISTED
}
```

---

## 4. Fundamentals Facade
**Endpoint**: `GET /stocks/{stock_code}/fundamentals`

Aggregated view of critical fundamental data (Valuation + Financials) for strategy filtering.

**Parameters**:
- `stock_code` (path, required): Stock code.

**Response**:
```json
{
  "stock_code": "600519",
  "pe_ttm": 30.5,           // Price-to-Earnings (TTM)
  "pb_ratio": 8.2,          // Price-to-Book
  "market_cap": 2200000000000.0,
  "revenue_ttm": 120000000000.0,
  "net_profit_ttm": 60000000000.0,
  "gross_margin": 91.5,     // Percentage
  "roe_ttm": 25.0,
  "revenue_growth_yoy": 15.2,
  "profit_growth_yoy": 18.5
}
```

---

## 5. Enhanced Stock List
**Endpoint**: `GET /stocks`

The existing stock list endpoint (EPIC-001) has been enhanced to include real-time market data when available.

**Response Enhancements**:
- `market_cap`: Real-time total market capitalization (Standardized unit: 亿元 implied, but typically raw from source currently)
- `turnover_ratio`: Real-time turnover rate (%)

```json
{
  "success": true,
  "data": [
    {
      "code": "600519",
      "name": "贵州茅台",
      "exchange": "SH",
      "market_cap": 22000.0, // 亿元
      "turnover_ratio": 0.5
      // ... other fields
    }
  ]
}
```

## Error Codes

For a list of standard error responses, see the [Error Codes reference](../error_codes.md).
