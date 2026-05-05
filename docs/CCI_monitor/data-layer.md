# CCI Monitor · 数据基础层 (Data Layer) 规范

> **核心原则**: 本次开发所有数据必须通过 **MySQL 数据接口 (get-stockdata API)** 获取。严禁直接调用 `akshare`、`tushare` 或其他第三方外部接口。

## 1. 接入点定义 (API Endpoints)

所有数据请求均指向 `get-stockdata` 服务。

| 业务数据 | API 路径 | 备注 |
|---|---|---|
| **指数/个股日线** | `GET /api/v1/quotes/history/{code}` | 支持 `start_date`, `end_date` |
| **指数成分股** | `GET /api/v1/market/sector/{index_name}/stocks` | 获取 L2-L5 各层级的成分列表 |
| **全市场列表** | `GET /api/v1/stocks/list` | 获取 L1 全市场监测的基础池 |
| **板块/行业列表** | `GET /api/v1/market/sector/list` | 获取 L3 行业层级的定义 |

## 2. 技术实现规范

### 2.1 抽象客户端 (API Client)

后端不再实现具体的抓取逻辑，而是实现一个统一的 HTTP 客户端。

```python
# backend/src/cci_monitor/data/api_client.py
import httpx
from ..core.exceptions import DataSourceError

class MySQLDataClient:
    """对接 get-stockdata MySQL API 的客户端."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_history(self, code: str, start: str, end: str):
        url = f"{self.base_url}/api/v1/quotes/history/{code}"
        params = {"start_date": start, "end_date": end, "adjust": "2"}
        resp = await self.client.get(url, params=params)
        if resp.status_code != 200:
            raise DataSourceError(f"API Error: {resp.text}")
        return resp.json()["data"]
```

### 2.2 数据标准化 (Mapping)

API 返回的字段名与 CCI 计算引擎所需的字段名映射如下：

| API 返回字段 | CCI 内部字段 | 说明 |
|---|---|---|
| `trade_date` | `date` | 交易日期 (YYYY-MM-DD) |
| `close_price` | `close` | 收盘价 (后复权) |
| `pct_chg` | `change_pct` | 涨跌幅 (%) |
| `vol` | `volume` | 成交量 |

### 2.3 异常处理与降级

1.  **连接失败**: 触发 `DataSourceUnavailableError`，系统尝试使用本地 Redis/Parquet 缓存。
2.  **数据缺失**: 若 API 返回 `count: 0`，抛出 `DataSourceEmptyError`。
3.  **限流**: 遵守 `get-stockdata` 的并发限制。

## 3. 验收标准

- [ ] `AkshareDataSource` 已被完全废弃或移除。
- [ ] 所有数据链路通过 `MySQLDataClient` 走内网 API。
- [ ] 支持通过环境变量 `GSD_API_URL` 配置接口地址。
- [ ] 单元测试使用 `httpx.ASGITransport` 或 `respx` 模拟 API 响应。
