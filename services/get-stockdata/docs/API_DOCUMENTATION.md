# API Documentation for Quant-Strategy Integration

This document outlines the API endpoints provided by the `get-stockdata` service for use by the `quant-strategy` microservice.

## Base URL
Default: `http://get-stockdata:8083` (Internal / Host Mode)

> [!TIP]
> 详细的分模块接口文档请参考：[API 文档索引表](api/README.md)

---

## 1. Actionable Quotes

### 1.1 Batch Real-time Quotes
**Endpoint:** `GET /api/v1/quotes/realtime`
**Parameters:** `codes` (CSV)
**Description:** Returns current price, volume, and L1 depth.

### 1.2 Real-time/Historical Tick Data
**Endpoint:** `GET /api/v1/quotes/tick/{stock_code}`
**Parameters:** `date` (YYYYMMDD, optional)
**Description:** High-frequency transaction-by-transaction data. Essential for **OFI (Order Flow Imbalance)** strategies.

### 1.3 Historical K-Line Data
**Endpoint:** `GET /api/v1/quotes/history/{stock_code}`
**Description:** Used for backtesting and calculating **VWAP**. 
**Details:** See [Detailed K-Line API Documentation](file:///home/bxgh/microservice-stock/services/get-stockdata/docs/api/stock_kline_api.md#1-data-retrieval-api).

---

## 2. Market & Sector Insight

### 2.1 Market Rankings
**Endpoint:** `GET /api/v1/market/ranking`
**Parameters:** `ranking_type`: `limit_up`, `人气`, `涨幅`, `volume`
**Description:** Identify market outliers and volatility.

### 2.2 Dragon Tiger List (龙虎榜)
**Endpoint:** `GET /api/v1/market/dragon_tiger`
**Parameters:** `date` (YYYY-MM-DD, optional)
**Description:** Track major institutional and hot-money movements (**Smart Money** monitoring).

### 2.3 Sector Analysis
**Endpoints:** 
- `GET /api/v1/market/sector/list` - Get full sector/industry list.
- `GET /api/v1/market/sector/{sector_code}/stocks` - Get stocks in a sector.
**Description:** Essential for top-down strategy execution.

### 2.4 Capital Flow
**Endpoint:** `GET /api/v1/market/capital_flow/{stock_code}`
**Description:** Real-time inflow/outflow metrics for a specific stock.

---

## 3. Financial & Valuation (EPIC-002)

### 3.1 Enhanced Finance Metrics
**Endpoint:** `GET /api/v1/finance/indicators/{stock_code}`
**Description:** Core financial indicators required by Story 2.1 and 2.2.

### 3.2 Valuation Ratios
**Endpoint:** `GET /api/v1/market/valuation/{stock_code}`
**Description:** Real-time PE, PB, and Market Cap. Supports Valuation Statistical Analysis (Story 2.3).

---

## 4. Universe Management

### 4.1 Stock Metadata & List
**Endpoints:** 
- `GET /api/v1/stocks/{stock_code}/info`
- `GET /api/v1/stocks/list`
**Description:** Basic info like listing date and full stock universe metadata.

---

## 5. Data Synchronization

### 5.1 Trigger K-Line Sync
**Endpoint:** `POST /api/v1/sync/kline`
**Description:** Triggers background sync task to update local K-line warehouse.

### 5.2 Check Sync Status
**Endpoint:** `GET /api/v1/sync/kline/status`
**Description:** Monitor the progress of current sync tasks.

**Full Synchronization Details:** See [K-Line Sync & Monitoring API](file:///home/bxgh/microservice-stock/services/get-stockdata/docs/api/stock_kline_api.md#2-synchronization-api).

---

## Data Standards
- **Stock Codes**: Standard 6-digit string (e.g., `"000001"`).
- **Timezone**: `Asia/Shanghai` (CST).
- **Format**: All responses are JSON; `NaN` in data sources is converted to `null`.
- **Latency**: Sub-50ms target for internal gRPC communication.
