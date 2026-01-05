# Level-1 Snapshot Data Acquisition Restored (QC Complete)

The `snapshot-recorder` service has been successfully restored and is now actively acquiring Level-1 snapshot data into ClickHouse. This restores a critical data stream that had been stale since 2025-12-22.

## Changes Implemented

### 1. New Dedicated Service
- Deployed `snapshot-recorder` as a standalone Docker service in `docker-compose.microservices.yml`.
- Configured persistent volumes for both Parquet storage (`/app/data/snapshots`) and ClickHouse writing.
- Standardized `PYTHONPATH`, module imports, and unbuffered logging (`python -u`).

### 2. Code Quality & Resilience Improvements
- **Configuration-Driven Pool**: Removed hardcoded lists. Now dynamically loads 318 stocks from [hs300_stocks.yaml](file:///home/bxgh/microservice-stock/services/get-stockdata/config/hs300_stocks.yaml).
- **Graceful Shutdown**: Implemented `SIGTERM`/`SIGINT` handling for clean resource release.
- **ClickHouse Resilience**: Added retry logic and explicit column mapping to handle schema defaults (e.g., `created_at`).
- **Data Source Robustness**: Optimized Mootdx connection logic to use already-discovered best IPs and immediate fallbacks.

### 3. Data Integrity & Mapping
- Fixed `ClickHouseWriter` to explicitly list columns during `INSERT`.
- Restored the correct `DualWriter` flow, ensuring data is persisted to both local Parquet files and ClickHouse.

## Verification Results

### Success Confirmation
The `snapshot-recorder` is now collecting data at approximately 3-second intervals for the HS300 stock pool.

- **Current Status**: Running
- **Records Today (2026-01-05)**: 8,000+ (growing)
- **Last Verification Time**: 2026-01-05 10:39:58
- **Average Round Duration**: 0.7s - 1.7s (for 318 stocks)

```bash
# Verification Command (ClickHouse)
curl -s "http://localhost:8123/?query=SELECT max(snapshot_time),count(*) FROM stock_data.snapshot_data WHERE trade_date = today()"
```

## Maintenance Notes
- **Stock Pool**: Manage symbols in `services/get-stockdata/config/hs300_stocks.yaml`.
- **Backups**: Parquet backups are stored in `services/get-stockdata/data/snapshots` on the host.
- **Scaling**: Batch size is currently 80, covering 318 stocks in 4 batches per round.
