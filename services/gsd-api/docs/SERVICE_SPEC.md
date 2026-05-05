# gsd-api 服务规格说明

> **版本**: v1.0  
> **更新时间**: 2026-01-17  
> **服务端口**: 8000  
> **状态**: ✅ 生产环境

---

## 1. 服务概述

`gsd-api` 是股票数据的只读查询服务，为上层应用提供统一的数据访问接口，从 ClickHouse 和 Redis 获取数据并返回。

### 1.1 核心职责

| 职责 | 描述 |
|------|------|
| 数据查询 | K 线、分笔、行情等数据查询 |
| 缓存层 | Redis 热点数据缓存 |
| 数据聚合 | 跨表数据整合 |
| 网关路由 | 对接 mootdx-api 实时数据 |

### 1.2 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI (Uvicorn) |
| 数据库 | ClickHouse (只读) |
| 缓存 | Redis |
| 数据处理 | Pandas |

---

## 2. API 接口规格

### 2.1 实时行情

```
GET /api/v1/quotes?codes={codes}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `codes` | string | ✅ | 股票代码，逗号分隔 |

**说明**: 代理到 mootdx-api 获取实时数据。

---

### 2.2 K 线数据

```
GET /api/v1/kline/{code}?start_date={date}&end_date={date}&frequency={d|w|m}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | path | ✅ | 股票代码 |
| `start_date` | string | ❌ | 起始日期 (YYYY-MM-DD) |
| `end_date` | string | ❌ | 结束日期 (YYYY-MM-DD) |
| `frequency` | string | ❌ | 频率: `d`/`w`/`m` (默认 `d`) |
| `adjust` | string | ❌ | 复权类型: `none`/`qfq`/`hfq` |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `trade_date` | string | 交易日期 |
| `open` | float | 开盘价 |
| `high` | float | 最高价 |
| `low` | float | 最低价 |
| `close` | float | 收盘价 |
| `volume` | int | 成交量 |
| `amount` | float | 成交额 |
| `turnover_rate` | float | 换手率 |

---

### 2.3 分笔数据

```
GET /api/v1/tick/{code}?date={YYYYMMDD}&limit={n}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | path | ✅ | 股票代码 |
| `date` | string | ❌ | 交易日期 (默认最近交易日) |
| `limit` | int | ❌ | 返回条数限制 |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `time` | string | 时间 |
| `price` | float | 成交价 |
| `volume` | int | 成交量 |
| `type` | string | 成交类型 |

---

### 2.4 市场数据

```
GET /api/v1/market/stats
```

**响应**:
```json
{
  "total_stocks": 5200,
  "up_count": 2800,
  "down_count": 2100,
  "flat_count": 300,
  "total_amount": 980000000000,
  "updated_at": "2026-01-17T15:00:00"
}
```

---

### 2.5 股票列表

```
GET /api/v1/stocks?market={sh|sz}&industry={industry}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `market` | string | ❌ | 市场: `sh`/`sz` |
| `industry` | string | ❌ | 行业筛选 |

---

### 2.6 财务数据

```
GET /api/v1/finance/{code}
```

**响应字段**:
- 基础财务指标
- 估值指标
- 盈利能力指标

---

### 2.7 内部接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/internal/warmup` | 缓存预热 |
| GET | `/api/v1/internal/stats` | 服务统计 |

---

## 3. 核心组件

### 3.1 数据访问层

**目录**: `src/data_access/`

| 模块 | 说明 |
|------|------|
| `clickhouse_client.py` | ClickHouse 连接客户端 |
| `redis_cache.py` | Redis 缓存操作 |
| `kline_repository.py` | K 线数据仓库 |
| `tick_repository.py` | 分笔数据仓库 |

---

### 3.2 网关层

**目录**: `src/gateway/`

| 模块 | 说明 |
|------|------|
| `mootdx_gateway.py` | mootdx-api 调用网关 |

---

## 4. 配置

### 4.1 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CLICKHOUSE_HOST` | 127.0.0.1 | ClickHouse 地址 |
| `CLICKHOUSE_PORT` | 9000 | ClickHouse 端口 |
| `REDIS_HOST` | 127.0.0.1 | Redis 地址 |
| `REDIS_PORT` | 6379 | Redis 端口 |
| `MOOTDX_API_URL` | http://mootdx-api:8003 | mootdx-api 地址 |
| `CACHE_TTL` | 300 | 缓存过期时间 (秒) |

---

## 5. 健康检查

```
GET /health
```

**响应**:
```json
{
  "status": "healthy",
  "clickhouse": "connected",
  "redis": "connected"
}
```

---

## 6. 部署

### 6.1 Docker 运行

```bash
docker build -t gsd-api .
docker run -p 8000:8000 \
  -e CLICKHOUSE_HOST=host.docker.internal \
  -e REDIS_HOST=host.docker.internal \
  gsd-api
```

### 6.2 本地开发

```bash
cd services/gsd-api
pip install -e ../../libs/gsd-shared
pip install -r requirements.txt
python src/main.py
```

---

## 7. API 文档

访问 Swagger UI: `http://localhost:8000/docs`

---

## 8. 依赖服务

| 服务 | 用途 | 必需 |
|------|------|------|
| ClickHouse | K 线/分笔数据 | ✅ |
| Redis | 缓存 | ✅ |
| mootdx-api | 实时行情 | ❌ |

---

## 9. 相关文档

| 文档 | 路径 |
|------|------|
| 共享数据模型 | `../../libs/gsd-shared/` |
