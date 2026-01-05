# 🌊 Data Flow

> **目的**: 可视化数据从采集到消费的完整路径，帮助 AI 理解系统数据流向。

---

## 整体数据架构

```mermaid
graph TB
    subgraph 外部数据源
        TDX[通达信服务器]
        BAO[Baostock API<br>云端]
        AK[AkShare API<br>云端]
        MYSQL_CLOUD[(MySQL<br>腾讯云)]
    end
    
    subgraph 本地微服务
        MAPI[mootdx-api]
        GSD[get-stockdata]
        SNP[snapshot-recorder]
        QS[quant-strategy]
        TO[task-orchestrator]
        GW[gsd-worker]
    end
    
    subgraph 本地存储
        CH[(ClickHouse<br>时序数据)]
        CH_REP[(ClickHouse<br>Replica)]
        REDIS[(Redis<br>缓存)]
    end
    
    subgraph 输出
        API[REST API]
        SIGNAL[策略信号]
    end
    
    TDX -->|TCP| MAPI
    BAO -->|HTTP| GSD
    AK -->|HTTP| GSD
    MYSQL_CLOUD -->|SSH Tunnel| GW
    
    MAPI -->|HTTP| GSD
    MAPI -->|HTTP| SNP
    
    GSD -->|写入| CH
    GSD -->|缓存| REDIS
    SNP -->|写入| CH
    
    CH <-->|复制| CH_REP
    
    TO -->|调度| GW
    GW -->|同步| CH
    
    QS -->|读取| REDIS
    QS -->|读取| GSD
    QS -->|生成| SIGNAL
    
    GSD --> API
```

---

## 数据流 1: 实时行情采集

```mermaid
sequenceDiagram
    participant TDX as 通达信服务器
    participant MAPI as mootdx-api
    participant SNP as snapshot-recorder
    participant CH as ClickHouse
    
    loop 09:30-15:00 (每3秒)
        SNP->>MAPI: GET /quotes/{codes}
        MAPI->>TDX: TCP 请求
        TDX-->>MAPI: 实时报价
        MAPI-->>SNP: JSON Response
        SNP->>CH: INSERT tick_data
    end
```

**关键表**: `stock_data.tick_data`

---

## 数据流 2: K 线日终同步

```mermaid
sequenceDiagram
    participant TO as task-orchestrator
    participant GW as gsd-worker
    participant MOOTDX as mootdx-api
    participant CH as ClickHouse
    
    Note over TO: 15:05 触发 daily_kline_sync
    TO->>GW: 启动容器
    GW->>MOOTDX: 获取日K线
    MOOTDX-->>GW: K线数据
    GW->>CH: INSERT stock_kline_daily
    GW-->>TO: 任务完成
```

**关键表**: `stock_data.stock_kline_daily`

---

## 数据流 3: 云端 K 线同步

```mermaid
sequenceDiagram
    participant MYSQL as MySQL (腾讯云)
    participant GW as gsd-worker
    participant CH as ClickHouse
    
    Note over GW: 通过 SSH Tunnel 连接云端 MySQL
    GW->>MYSQL: SELECT * FROM kline_data
    MYSQL-->>GW: K线数据
    GW->>CH: INSERT stock_kline_daily
    GW->>CH: 校验数据一致性
```

**数据一致性校验**:
1. Verify-After-Write: 写入后立即校验
2. Weekly Deep Audit: 周日全量聚合校验

---

## 数据流 4: 策略信号生成

```mermaid
sequenceDiagram
    participant QS as quant-strategy
    participant REDIS as Redis
    participant GSD as get-stockdata
    
    QS->>REDIS: 获取缓存数据
    alt 缓存命中
        REDIS-->>QS: 返回数据
    else 缓存未命中
        QS->>GSD: GET /api/v1/kline/{code}
        GSD-->>QS: K线数据
        QS->>REDIS: 缓存数据
    end
    QS->>QS: 策略计算 (OFI/Smart Money)
    QS-->>QS: 生成交易信号
```

---

## ClickHouse 复制

```mermaid
graph LR
    subgraph Server41
        CK41[ClickHouse Node 1]
        K41[Keeper Leader]
    end
    
    subgraph Server58
        CK58[ClickHouse Node 2]
        K58[Keeper Follower]
    end
    
    CK41 <-->|Replication :9009| CK58
    K41 <-->|Raft Consensus :9234| K58
```

**引擎**: `ReplicatedReplacingMergeTree`

---

## 关键数据表

| 表名 | 存储 | 用途 | 数据量级 |
|------|------|------|----------|
| `stock_kline_daily` | ClickHouse | 日K线 | ~17M 行 |
| `tick_data` | ClickHouse | 分笔数据 | 持续增长 |
| `sync_progress` | MySQL (云) | 同步进度 | ~ |
| `sync_execution_logs` | MySQL (云) | 同步日志 | ~ |
