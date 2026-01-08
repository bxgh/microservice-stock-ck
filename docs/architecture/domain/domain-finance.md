# Domain Architecture: Finance & Valuation

## 1. Introduction
This document details the architecture for the Finance & Valuation sub-domain of the `get-stockdata` service. It focuses on acquiring and serving valuation metrics, financial indicators, and industry statistics, often requiring complex proxy handling for external sources.

## 2. Hybrid Proxy Architecture

To resolve proxy compatibility issues between different data source protocols (HTTP/HTTPS vs TCP) in the internal network environment, the system adopts a Hybrid Proxy Architecture:

```mermaid
graph TD
    subgraph "Get Stock Data Container"
        A[Akshare Provider]
        M[Mootdx Provider]
        P[Proxychains4]
        
        A -- "HTTP GET (Direct)" --> PROXY
        M -- "TCP Connect" --> P
        P -- "Socks/HTTP Tunnel" --> PROXY
    end
    
    subgraph "Infrastructure"
        PROXY[Squid Proxy (192.168.151.18:3128)]
    end
    
    subgraph "External"
        Internet[Internet Resources]
        RemoteAPI[Remote Akshare API]
    end
    
    PROXY --> Internet
    PROXY --> RemoteAPI
```

1. **Explicit Proxy**: 
   - Component: **AkshareProvider** (aiohttp based)
   - Mechanism: Direct `HTTP_PROXY` environment variable configuration
   - Path: `aiohttp` -> `192.168.151.18:3128` (Direct) -> `Remote API`
   - **Key Config**: Configure `localnet` in `proxychains.conf` to exclude proxy server IP to prevent infinite loops.

2. **Transparent Chain**:
   - Component: **MootdxProvider** (TCP Socket based)
   - Mechanism: Intercept TCP calls via `proxychains4`
   - Path: `Socket` -> `proxychains` -> `192.168.151.18:3128` -> `Internet`

3. **Remote Akshare API**:
   - Deployed **v2.5.0** remote service providing `Baidu` valuation interfaces and `Meta` info interfaces, replacing unstable local calculations.

## 3. API Interface

### 3.1 Valuation & Finance API (EPIC-002)

**Endpoints:**
- `GET /api/v1/market/valuation/{symbol}` - Get real-time valuation (PE/PB/Market Cap) (Remote Akshare)
- `GET /api/v1/market/valuation/{symbol}/history` - Get historical valuation trends
- `GET /api/v1/finance/indicators/{symbol}` - Get enhanced financial indicators
- `GET /api/v1/finance/industry/{code}/stats` - Get industry statistical data
