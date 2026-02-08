# mootdx-source 服务架构 (Unified Gateway Pattern)

**版本**: 2.0.0-hybrid
**该当日期**: 2026-02-08
**状态**: 生产就绪

---

## 1. 服务定位

`mootdx-source` 是系统中的**统一数据网关（Unified Data Gateway）**，通过 **gRPC** 协议为上游微服务提供标准化的数据获取接口。它屏蔽了底层异构数据源（MySQL, ClickHouse, Redis, HTTP API, TCP）的复杂性。

```mermaid
graph TB
    subgraph Clients
        A[get-stockdata]
        B[quant-strategy]
    end

    subgraph "mootdx-source (Unified Gateway)"
        GW[gRPC Service]
        ROUTER[Routing Logic]
        VAL[Validation Layer]
    end

    subgraph "Data Sources (Heterogeneous)"
        MYSQL[(MySQL<br/>AlwaysUp)]
        CH[(ClickHouse<br/>StockData)]
        MOOTDX_API[Mootdx API<br/>(HTTP Proxy)]
        CLOUD_API[Cloud API<br/>(AkShare/Baostock)]
    end

    A --> GW
    B --> GW
    GW --> ROUTER
    ROUTER --> VAL
    VAL --> MYSQL
    VAL --> CH
    VAL --> MOOTDX_API
    VAL --> CLOUD_API
```

### 核心能力
1.  **统一协议**: 所有数据请求统一走 gRPC (Protobuf)，无需关心底层是 SQL 还是 HTTP。
2.  **智能路由**: 基于 `DataType` 自动路由到最优数据源（例如 `ISSUE_PRICE` -> MySQL, `FEATURES` -> ClickHouse）。
3.  **连接池管理**: 内置 MySQL (`aiomysql`) 和 ClickHouse (`asynch`) 连接池，保障高并发稳定性。
4.  **数据标准化**: 自动处理证券代码后缀 (`.SZ/.SH`) 和字段映射 (`ts_code` -> `code`)。

---

## 2. 核心架构

### 组件关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                        mootdx-source                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    MooTDXService                          │  │
│  │  (gRPC Servicer, 路由入口, 数据验证)                       │  │
│  └───────────┬───────────────────────────────────────────────┘  │
│              │ 路由分发 (RouteConfig)                           │
│  ┌───────────▼───────────────────────────────────────────────┐  │
│  │                   Handler Layer                           │  │
│  │  ┌─────────────────┐  ┌─────────────────┐ ┌────────────┐  │  │
│  │  │ MySQLHandler    │  │ ClickHouseHdlr  │ │ CloudClient│  │  │
│  │  │ (发行价/行业)   │  │ (特征/分笔)     │ │ (历史/榜单)│  │  │
│  │  └────────┬────────┘  └────────┬────────┘ └─────┬──────┘  │  │
│  └───────────┼────────────────────┼────────────────┼─────────┘  │
│              │                    │                │            │
│  ┌───────────▼───────────┐ ┌──────▼────────────┐ ┌─▼──────────┐ │
│  │ MySQL (AlwaysUp)      │ │ ClickHouse (Data) │ │ ExternalAPI│ │
│  │ - stock_basic_info    │ │ - features        │ │ - Akshare  │ │
│  │ - stock_industry_sw   │ │ - intraday_local  │ │ - Baostock │ │
│  └───────────────────────┘ └───────────────────┘ └────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 关键模块说明

| 模块 | 文件 | 职责 |
|:---|:---|:---|
| **MooTDXService** | `service.py` | 服务入口，负责 gRPC 请求解析、路由分发、数据验证及异常处理。 |
| **MySQLHandler** | `handlers/mysql_handler.py` | **[新增]** 管理 MySQL 连接池，提供基础信息查询（发行价、申万行业）。 |
| **ClickHouseHandler** | `handlers/clickhouse_handler.py` | **[新增]** 管理 ClickHouse 连接池，提供高性能特征矩阵与分笔数据查询。 |
| **MootdxAPIClient** | `mootdx_client.py` | 调用 `mootdx-api` 微服务获取实时行情（解决了直连不稳定问题）。 |
| **CloudAPIClient** | `cloud_client.py` | 聚合调用 AkShare、Baostock 等外部 HTTP 数据源。 |

---

## 3. 数据路由表 (Routing Table)

| DataType | Handler | 数据源 | 备注 |
|:---|:---|:---|:---|
| `QUOTES` | `MootdxAPIClient` | `mootdx-api` | 实时行情，高频调用 |
| `TICK` | `MootdxAPIClient` | `mootdx-api` | 分笔数据，高频调用 |
| `ISSUE_PRICE` | `MySQLHandler` | `MySQL` | **新增**，取自 `stock_basic_info` |
| `SW_INDUSTRY` | `MySQLHandler` | `MySQL` | **新增**，取自 `stock_industry_sw` |
| `FEATURES` | `ClickHouseHandler` | `ClickHouse` | **新增**，取自 `stock_data.features` |
| `HISTORY` | `CloudAPIClient` | `Baostock` | 历史 K 线，有本地降级策略 |
| `FINANCE` | `CloudAPIClient` | `AkShare` | 财务数据 |

---

## 4. 基础设施依赖

- **Nacos**: 服务注册与发现 (`127.0.0.1:8848`)。
- **MySQL**: 存储基础元数据 (`alwaysup` 库)，通常使用 Docker 部署 (`36301` 端口)。
- **ClickHouse**: 存储海量行情与特征数据 (`stock_data` 库)，使用 Docker 部署 (`9000` 端口)。
- **mootdx-api**: 独立的 Python 服务，专职处理通达信协议连接 (`8003` 端口)。

## 5. 扩展指南

详见 [Extension Guide](./extension_guide.md)
