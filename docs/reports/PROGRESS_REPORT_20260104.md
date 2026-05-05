# Progress Report: System Repair & Architecture Upgrade (2026-01-04)

## 1. System Stability Repairs

### 1.1 `task-orchestrator` Recovery
- **Issue**: Service stuck in restart loop due to `OperationalError: (2003, "Can't connect to MySQL server on '127.0.0.1'")`.
- **Root Cause**: Invalid GOST tunnel configuration attempting to route MySQL traffic via Squid proxy instead of the required SSH tunnel.
- **Resolution**: 
  - Deployed proper systemd service `/etc/systemd/system/gost-mysql-tunnel.service`.
  - Configured forwarding chain: `tcp://:36301/43.145.51.23:26300 -> http://127.0.0.1:8118`.
  - Verified connectivity on both Server 41 and Server 58.

### 1.2 `mootdx-api` Fix
- **Issue**: Container failed strictly due to `IndentationError`.
- **Resolution**: Corrected syntax error in `handlers/mootdx_handler.py` and rebuilt the image.

## 2. Infrastructure Optimization

### 2.1 ClickHouse System Log Cleanup
- **Optimization**: ClickHouse system logs (`trace_log`, `text_log`, etc.) were consuming ~14GB (38% of disk usage).
- **Implementation**:
  - Added `weekly_clickhouse_log_cleanup` task to `task-orchestrator`.
  - Schedule: Every Sunday at 03:00.
  - Policy: Keep 7 days for operational logs, 14 days for query logs.
  - Result: Disk usage reduced from 36.56 GiB to 22.70 GiB.

## 3. Architecture Upgrade: Active-Active ClickHouse Cluster

Established a Multi-Master Replication architecture between **Server 41** and **Server 58**, enabling real-time data synchronization and high availability.

### 3.1 Components
- **ClickHouse Keeper**: Embedded coordination service replacing ZooKeeper.
  - Server 41: Keeper Leader
  - Server 58: Keeper Follower
- **Replication Protocol**:
  - Inter-server communication strictly on port `9009`.
  - Configured `interserver_http_host` to solve network addressing issues in Docker.

### 3.2 Data Migration
Migrated `stock_kline_daily` (17M+ rows) from single-node engine to replicated engine.

- **Old Engine**: `ReplacingMergeTree`
- **New Engine**: `ReplicatedReplacingMergeTree`
- **Result**:
  - Server 41 Row Count: **17,475,207**
  - Server 58 Row Count: **17,475,207**
  - Write Latency: <1s sync delay.

### 3.3 Topology Diagram

```mermaid
graph LR
    subgraph Server41 [Server 41]
        CK41[ClickHouse Node 1]
        K41[Keeper Leader]
        Orch41[Task Orchestrator]
    end
    
    subgraph Server58 [Server 58]
        CK58[ClickHouse Node 2]
        K58[Keeper Follower]
        Orch58[Task Orchestrator]
    end
    
    CK41 <-->|Replication (9009)| CK58
    K41 <-->|Raft Consensus (9234)| K58
    CK41 -->|Metadata| K41
    CK58 -->|Metadata| K58
    
    Orch41 -->|Write| CK41
    Orch58 -->|Write| CK58
```

## 4. Next Steps
- Monitor the stability of the 2-node Keeper cluster (susceptible to split-brain if one node fails).
- Consider adding a 3rd Keeper witness node for robust consensus.
- Migrate other critical tables (`tick_data`, `financials`) to replicated engines.
