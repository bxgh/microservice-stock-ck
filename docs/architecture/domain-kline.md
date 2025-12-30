# Domain Architecture: K-Line Data Warehouse

## 1. Introduction
This document details the architecture for the K-Line Data Warehouse, a sub-domain of the `get-stockdata` service. It focuses on the synchronization, storage, and retrieval of historical daily K-line data.

## 2. K-Line Data Warehouse Architecture (EPIC-010)

To support high-performance historical backtesting, the system implements a local data warehouse based on ClickHouse.

**Data Flow Architecture:**
1. **Source**: Tencent Cloud MySQL (`stock_kline_daily` table)
2. **Transport**: 
   - **GOST Tunnel**: Bypass proxy wall (`127.0.0.1:36301` -> `Remote:26300`)
   - **Sync Script**: Full/Incremental sync script (`sync_kline_to_clickhouse.py`)
3. **Storage**: ClickHouse Local
   - Engine: `ReplacingMergeTree`
   - Partition: By Month `toYYYYMM(trade_date)`
   - Sort Key: `(stock_code, trade_date)`
4. **Service Layer**:
   - **Driver**: `asynch` (Async I/O)
   - **DAO**: `ClickHouseKLineDAO` (Primary) -> `KLineDAO` (MySQL Fallback)

**Sync Strategy:**
- **Full Sync**: Initial full synchronization (8M+ records)
- **Increment Sync**: Daily scheduled incremental sync (based on `created_at`)

## 3. Operational Guide

### 3.1 Synchronization Commands

Run the following commands inside the `get-stockdata` container (or via `docker exec`):

**1. Full Synchronization (Initial)**
```bash
docker exec -it get-stockdata-api-dev python scripts/sync_kline_to_clickhouse.py --mode full --batch-size 10000
```

**2. Incremental Sync (Daily Scheduled)**
```bash
# Sync data created in the last 48 hours (Recommended for daily cron)
docker exec -it get-stockdata-api-dev python scripts/sync_kline_to_clickhouse.py --mode created_at --hours 48
```

**3. Smart Sync (Auto-detect)**
```bash
# Sync data after the latest date in ClickHouse
docker exec -it get-stockdata-api-dev python scripts/sync_kline_to_clickhouse.py --mode smart
```

## 4. API Interface

### 3.1 Basic Quotes API (Quotes & Info)

**Endpoints:**
- `GET /api/v1/quotes/realtime?codes=...` - Batch get real-time quotes (Mootdx)
- `GET /api/v1/stock/info/{code}` - Get stock metadata (Akshare/Remote)
- `GET /api/v1/stock/search/{query}` - Search stocks
- `GET /api/v1/quotes/history/{code}` - Get historical K-line data (ClickHouse/MySQL)

### 3.2 Stock Data Model

**Stock Data Model Design:**
- **Basic Info**: Code, Name, Price, Change Amount, Change Percent
- **Trading Info**: Volume, Market Cap, PE Ratio
- **Timestamp**: Data Update Time
