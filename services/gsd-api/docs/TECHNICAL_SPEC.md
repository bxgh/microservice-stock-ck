# GSD-API 技术规范

> **版本**: 1.0  
> **服务类型**: 长驻查询服务  
> **基于**: get-stockdata 三层架构

---

## 1. 服务定位

**gsd-api** 是从 get-stockdata 拆分出的**只读查询服务**，负责：
- 实时行情查询
- 历史K线查询
- 财务数据查询
- 市场数据查询
- 股票元数据查询

**不包含**：数据同步、质量检测、修复（由 gsd-worker 负责）

---

## 2. 架构模式 (必须遵循)

### 2.1 三层架构

```
┌─────────────────────────────────────────┐
│  API Routes Layer (路由层)               │
│  - HTTP 请求处理                         │
│  - 参数验证                              │
│  - 响应格式化                            │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Data Services Layer (服务层)            │
│  - 业务逻辑封装                          │
│  - 缓存管理 (Redis)                      │
│  - 数据聚合                              │
│  - 数据源降级                            │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Data Providers Layer (数据源层)         │
│  - Mootdx (实时行情)                     │
│  - ClickHouse (历史数据)                 │
│  - AkShare API (财务/估值)               │
└─────────────────────────────────────────┘
```

**参考**: `get-stockdata/docs/architecture/DATA_ACQUISITION_ARCHITECTURE.md`

---

## 3. 核心服务清单

| Service | 功能 | 数据源 | 缓存TTL |
|:--------|:-----|:-------|:--------|
| **QuotesService** | 实时行情 | Mootdx, Easyquotation | 5秒 |
| **HistoryService** | 历史K线 | ClickHouse, Baostock | 1小时 |
| **FinancialService** | 财务报表 | AkShare, Baostock | 1天 |
| **ValuationService** | 估值数据 | AkShare | 1小时 |
| **IndustryService** | 行业数据 | AkShare, Pywencai | 1小时 |
| **MarketService** | 市场榜单 | AkShare | 5分钟 |
| **StocksService** | 股票元数据 | MySQL, Redis | 1天 |

---

## 4. API 端点规范

### 4.1 实时行情
```
GET /api/v1/quotes/realtime?codes=000001,600519
GET /api/v1/quotes/tick/{stock_code}?date=20240102
```

### 4.2 历史数据
```
GET /api/v1/quotes/history/{stock_code}?start_date=2024-01-01&end_date=2024-01-31
GET /api/v1/kline/daily/{stock_code}
```

### 4.3 财务数据
```
GET /api/v1/finance/indicators/{stock_code}
GET /api/v1/market/valuation/{stock_code}
```

### 4.4 市场数据
```
GET /api/v1/market/ranking?ranking_type=limit_up
GET /api/v1/market/dragon_tiger?date=2024-01-02
GET /api/v1/market/sector/list
```

### 4.5 股票元数据
```
GET /api/v1/stocks/list
GET /api/v1/stocks/{stock_code}/info
```

**完整规范**: `get-stockdata/docs/API_DOCUMENTATION.md`

---

## 5. 技术要求

### 5.1 并发安全 ⚠️ 必须

所有 Service 必须使用 `asyncio.Lock` 保护共享状态：

```python
class QuotesService:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._cache = {}
    
    async def get_realtime(self, codes: list):
        async with self._lock:
            # 保护共享状态
            pass
```

### 5.2 缓存策略

```python
CACHE_TTL = {
    "realtime": 5,       # 实时数据 5秒
    "tick": 60,          # 分笔数据 1分钟
    "daily_kline": 3600, # 日线 1小时
    "financial": 86400,  # 财务数据 1天
    "metadata": 86400,   # 元数据 1天
}
```

### 5.3 数据源降级

```python
async def get_financial_data(self, code: str):
    # 主数据源
    try:
        data = await self.akshare_provider.fetch(...)
        if data.success:
            return data.data
    except Exception as e:
        logger.warning(f"Primary source failed: {e}")
    
    # 降级到备用源
    try:
        data = await self.baostock_provider.fetch(...)
        if data.success:
            return data.data
    except Exception as e:
        logger.error(f"Fallback failed: {e}")
    
    return None
```

### 5.4 资源管理

```python
@app.on_event("startup")
async def startup():
    # 初始化所有服务
    await app.state.quotes_service.initialize()
    await app.state.financial_service.initialize()

@app.on_event("shutdown")
async def shutdown():
    # 清理资源
    await app.state.quotes_service.close()
    await app.state.financial_service.close()
```

---

## 6. 网络配置

### 6.1 Docker 配置

```yaml
# docker-compose.yml
services:
  gsd-api:
    build: ./services/gsd-api
    network_mode: host  # ⚠️ 必须！Mootdx TCP 连接需要
    environment:
      # ClickHouse
      - CLICKHOUSE_HOST=localhost
      - CLICKHOUSE_PORT=9000
      
      # Redis
      - REDIS_HOST=localhost
      - REDIS_PORT=6379
      
      # 云端 API (通过代理)
      - PROXY_URL=http://192.168.151.18:3128
      - AKSHARE_API_URL=http://124.221.80.250:8003
      - BAOSTOCK_API_URL=http://124.221.80.250:8001
```

### 6.2 代理使用规则

| 数据源 | 代理 | 说明 |
|:-------|:-----|:-----|
| Mootdx (TCP) | ❌ 不使用 | 直连通达信服务器 |
| ClickHouse | ❌ 不使用 | 本地连接 |
| Redis | ❌ 不使用 | 本地连接 |
| AkShare API | ✅ 使用 3128 | 云端 HTTP 请求 |
| Baostock API | ✅ 使用 3128 | 云端 HTTP 请求 |

---

## 7. 数据模型

### 7.1 使用 gsd-shared

```python
# ❌ 错误 - 使用本地模型
from models.stock_models import StockInfo

# ✅ 正确 - 使用共享模型
from gsd_shared.models import StockInfo
```

### 7.2 响应格式

```python
# 统一响应格式
{
    "success": true,
    "data": {...},
    "message": "操作成功"
}

# 错误响应
{
    "success": false,
    "error": "错误信息",
    "code": 404
}
```

---

## 8. 性能要求

| 指标 | 目标 |
|:-----|:-----|
| API 响应时间 | P95 < 100ms |
| 并发请求 | 支持 100 QPS |
| 缓存命中率 | > 80% |
| 服务可用性 | > 99.9% |

---

## 9. 监控指标

### 9.1 Prometheus 指标

```python
from prometheus_client import Counter, Histogram

# 请求计数
api_requests_total = Counter(
    'gsd_api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

# 响应时间
api_request_duration = Histogram(
    'gsd_api_request_duration_seconds',
    'API request duration',
    ['endpoint']
)

# 缓存命中率
cache_hits_total = Counter(
    'gsd_api_cache_hits_total',
    'Cache hits',
    ['cache_type']
)
```

### 9.2 健康检查

```python
@router.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "clickhouse": await check_clickhouse(),
            "redis": await check_redis(),
            "mootdx": await check_mootdx()
        }
    }
```

---

## 10. 开发检查清单

### 代码质量
- [ ] 所有 Service 使用 `asyncio.Lock`
- [ ] 实现资源清理 (`close` 方法)
- [ ] 添加详细日志
- [ ] 错误处理完整

### 性能优化
- [ ] Redis 缓存配置正确
- [ ] 缓存 TTL 合理
- [ ] 数据源降级逻辑

### 网络配置
- [ ] `network_mode: host` 已配置
- [ ] 代理环境变量已设置
- [ ] ClickHouse/Redis 连接正常

### 数据模型
- [ ] 所有导入改为 `gsd_shared.models`
- [ ] 响应格式统一
- [ ] 字段类型一致

### 测试
- [ ] 单元测试覆盖率 > 80%
- [ ] 并发测试通过
- [ ] 集成测试通过

---

## 11. 参考文档

- [DATA_ACQUISITION_ARCHITECTURE.md](file:///home/bxgh/microservice-stock/services/get-stockdata/docs/architecture/DATA_ACQUISITION_ARCHITECTURE.md) - 架构模式
- [API_DOCUMENTATION.md](file:///home/bxgh/microservice-stock/services/get-stockdata/docs/API_DOCUMENTATION.md) - API 规范
- [CODING_STANDARDS.md](file:///home/bxgh/microservice-stock/services/get-stockdata/docs/CODING_STANDARDS.md) - 编码规范
- [gsd-shared 设计](file:///home/bxgh/microservice-stock/services/get-stockdata/docs/architecture/task_scheduling/07_gsd_shared_design.md) - 数据模型

---

**维护**: 随 gsd-api 开发同步更新  
**版本**: 1.0 (2026-01-02)
