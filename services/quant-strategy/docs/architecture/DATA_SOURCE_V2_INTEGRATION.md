# Quant-Strategy 数据集成架构文档 (v2.0)

## 1. 概述

本计划文档描述了 `quant-strategy` 微服务如何接入重构后的 `get-stockdata` (v2.0) 混合数据源架构。新架构通过“云端+本地”的双轨模式，解决了高频实时行情与大规模基础数据的性能与稳定性冲突。

---

## 2. 核心架构图 (EPIC-008 混合模式)

```mermaid
graph TD
    subgraph Quant-Strategy
        QS[Strategy Engine] --> SDA[StockDataProvider]
    end

    subgraph Get-StockData Gateway (Port 8083)
        SDA --> API[API Routes Layer]
        API --> SVC[Data Services Layer]
        SVC --> GW[DataSourceGateway]
    end

    subgraph Data Providers
        GW -->|gRPC / Local| MT[Mootdx Source]
        GW -->|HTTP / Proxy| AK[AkShare Cloud]
        GW -->|HTTP / Proxy| BS[Baostock Cloud]
        GW -->|HTTP / Proxy| WC[Pywencai Cloud]
    end

    subgraph Infrastructure
        MT ---|Host Network| TDX[TDX HQ Server]
        AK ---|3128 Proxy| CLOUD[Cloud Data Services]
    end

    style QS fill:#f9f,stroke:#333,stroke-width:2px
    style GW fill:#ff9,stroke:#333,stroke-width:2px
    style TDX fill:#bfb,stroke:#333,stroke-width:2px
```

---

## 3. 分层职能说明

### 3.1 应用层 (API Routes)
- **职责**: 暴露 RESTful 接口供 `quant-strategy` 调用。
- **关键端点**:
    - `/api/v1/quotes/realtime`: 批量行情获取。
    - `/api/v1/finance/indicators/{code}`: 财务指标。
    - `/api/v1/market/valuation/{code}/history`: 估值带分析数据。
    - `/api/v1/gateway/data/history`: 通过 gRPC 转发的专业历史数据获取。

### 3.2 数据服务层 (Service Layer)
- **职能**: 业务逻辑聚合、多级缓存管理（In-memory + Redis）。
- **降级逻辑**: 当主数据源（如 Mootdx）不可用时，自动切换至备选源（如 Easyquotation 或 AkShare）。

### 3.3 数据源层 (Provider Layer)
- **Mootdx (本地直连)**: 专注于实时 L1 行情与分笔数据。采用 Host Network 模式直接 TCP 连接通达信节点。
- **云端三剑客 (AkShare/Baostock/Pywencai)**: 
    - 运行在公网节点，通过 Squid 代理 (3128) 对内网暴露。
    - 负责非实时、大规模的基本面、历史与选股数据。

---

## 4. 关键数据流示例

### 4.1 策略选股行情获取 (实时)
1. `quant-strategy` 发起批量请求：`GET /quotes/realtime?codes=600519,000001...`
2. `get-stockdata` 检查 **SnapShot Cache** (3-5秒过期)。
3. 若缓存失效，通过 `DataSourceGateway` 发起 gRPC 调用至 `mootdx-source`。
4. `mootdx-source` 维持与通达信服务器的长连接，秒级返回结果。

### 4.2 Alpha 评分数据获取 (静态/财务)
1. `quant-strategy` 请求 `/finance/indicators/600519`。
2. `get-stockdata` 优先从 **Redis 永久缓存**（针对已发布财报）读取。
3. 若未命中，通过 **AkShare Provider** 经过云端代理抓取。

---

## 5. 对 Quant-Strategy 的影响与后续改进

| 改进项 | 描述 | 预期收益 |
| :--- | :--- | :--- |
| **异步 ID 获取** | 接入云端 /api/v1/stocks 字典服务 | 保证全市场代码同步一致 |
| **gRPC 历史数据** | 使用网关的 history 路由 | 获得前复权/后复权的专家级 K 线 |
| **延迟优化** | 容器间网络由 Bridge 转为 Host (选配) | 行情延迟从 500ms 降低至 100ms 以内 |

---
**版本**: 2.0  
**最后更新**: 2025-12-21  
**状态**: 已归档至 `quant-strategy/docs/architecture/`
