# mootdx-api 服务规格说明

> **版本**: v1.0  
> **更新时间**: 2026-01-17  
> **服务端口**: 8003  
> **状态**: ✅ 生产环境

---

## 1. 服务概述

`mootdx-api` 是通达信（TDX）数据源的 HTTP REST API 网关服务，封装了 mootdx/pytdx 库，为上层服务提供统一的股票数据接口。

### 1.1 核心职责

| 职责 | 描述 |
|------|------|
| 连接池管理 | 多 TDX 节点连接池，实现负载均衡和故障切换 |
| 数据获取 | 实时行情、分笔成交、K线历史、股票列表等 |
| 异步封装 | 将同步的 mootdx 调用包装为异步接口 |
| Redis Stream 消费 | 支持通过 Redis Stream 接收批量数据请求 |

### 1.2 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI (Uvicorn) |
| TDX 客户端 | mootdx + pytdx (Monkeypatch) |
| 数据处理 | Pandas |
| 连接池 | 自研 `TDXClientPool` |
| 异步 | asyncio + run_in_executor |

---

## 2. API 接口规格

### 2.1 实时行情

```
GET /api/v1/quotes?codes={codes}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `codes` | string | ✅ | 股票代码，逗号分隔 (如 `600519,000001`) |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | string | 股票代码 |
| `name` | string | 股票名称 |
| `open` | float | 开盘价 |
| `high` | float | 最高价 |
| `low` | float | 最低价 |
| `price` | float | 现价 |
| `bid1-5` | float | 五档买价 |
| `ask1-5` | float | 五档卖价 |
| `volume` | int | 成交量 |
| `amount` | float | 成交额 |

**示例**:
```bash
curl "http://localhost:8003/api/v1/quotes?codes=600519,000001"
```

---

### 2.2 分笔成交

```
GET /api/v1/tick/{code}?date={YYYYMMDD}&start={n}&offset={n}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | path | ✅ | 股票代码 |
| `date` | int | ❌ | 交易日期 (整数格式，如 `20260117`)，不传则获取当日 |
| `start` | int | ❌ | 起始位置 (默认 0) |
| `offset` | int | ❌ | 获取数量 (默认 800，最大 10000) |

**响应字段 (已标准化)**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `time` | string | 时间 (HH:MM) |
| `price` | float | 成交价 |
| `volume` | int | 成交量 (股) |
| `type` | string | 买卖类型 (`BUY`/`SELL`/`NEUTRAL`) |

**示例**:
```bash
# 当日分笔
curl "http://localhost:8003/api/v1/tick/600519"

# 历史分笔
curl "http://localhost:8003/api/v1/tick/600519?date=20260115"
```

> **注意**: 当日分笔使用 `transaction()` 方法，历史分笔使用 `transactions()` 方法，两者参数格式不同。

---

### 2.3 历史K线

```
GET /api/v1/history/{code}?frequency={d|w|m}&offset={n}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | path | ✅ | 股票代码 |
| `frequency` | string | ❌ | 频率: `d`=日线, `w`=周线, `m`=月线 (默认 `d`) |
| `offset` | int | ❌ | 数据条数 (默认 500，最大 800) |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | string | 日期 |
| `open` | float | 开盘价 |
| `high` | float | 最高价 |
| `low` | float | 最低价 |
| `close` | float | 收盘价 |
| `volume` | int | 成交量 |
| `amount` | float | 成交额 |

**示例**:
```bash
curl "http://localhost:8003/api/v1/history/600519?frequency=d&offset=100"
```

> **限制**: mootdx 不支持复权数据，需配合 `/xdxr` 接口计算复权价。

---

### 2.4 股票列表

```
GET /api/v1/stocks?market={0|1}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `market` | int | ❌ | 市场: `0`=深圳, `1`=上海, 不传=全市场 |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | string | 股票代码 |
| `name` | string | 股票名称 (可能为空) |
| `market` | int | 市场代码 |

**示例**:
```bash
# 全市场
curl "http://localhost:8003/api/v1/stocks"

# 仅上海
curl "http://localhost:8003/api/v1/stocks?market=1"
```

> **注意**: 返回约 48,000+ 条记录，包含股票、ETF、债券等多种证券类型。

---

### 2.5 财务基础信息

```
GET /api/v1/finance/{code}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | path | ✅ | 股票代码 |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | string | 股票代码 |
| `liutongguben` | float | 流通股本 |
| `zongguben` | float | 总股本 |
| `province` | string | 省份 |
| `industry` | string | 行业 |
| `ipo_date` | string | 上市日期 |
| `updated_date` | string | 更新日期 |

---

### 2.6 除权除息

```
GET /api/v1/xdxr/{code}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | path | ✅ | 股票代码 |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `year` | int | 年 |
| `month` | int | 月 |
| `day` | int | 日 |
| `category` | int | 类别代码 |
| `fenhong` | float | 分红 (每股) |
| `songzhuangu` | float | 送转股比例 |
| `peigu` | float | 配股比例 |
| `peigujia` | float | 配股价格 |
| `suogu` | float | 缩股比例 |
| `panqianliutong` | float | 盘前流通股本 |
| `panhouliutong` | float | 盘后流通股本 |

> **用途**: 用于计算复权价格，历史分红记录完整。

---

### 2.7 指数K线

```
GET /api/v1/index/bars/{code}?frequency={d|w|m}&offset={n}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | path | ✅ | 指数代码 (如 `000001`=上证指数, `399001`=深成指) |
| `frequency` | string | ❌ | 频率: `d`=日线, `w`=周线, `m`=月线 (默认 `d`) |
| `offset` | int | ❌ | 数据条数 (默认 500，最大 800) |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | string | 日期 |
| `open` | float | 开盘点位 |
| `high` | float | 最高点位 |
| `low` | float | 最低点位 |
| `close` | float | 收盘点位 |
| `volume` | int | 成交量 |
| `amount` | float | 成交额 |
| `up_count` | int | 上涨家数 |
| `down_count` | int | 下跌家数 |

---

## 3. 核心组件

### 3.1 MootdxHandler

**文件**: `src/handlers/mootdx_handler.py`

通达信数据源处理器，管理连接池生命周期，提供数据获取接口。

```python
class MootdxHandler:
    """
    核心方法:
    - initialize() -> None     # 初始化连接池
    - close() -> None          # 关闭连接池
    - get_pool_status() -> dict  # 获取连接池状态
    - acquire_client() -> AsyncContextManager  # 获取独占客户端
    
    数据方法:
    - get_quotes(codes, params) -> DataFrame
    - get_tick(codes, params) -> DataFrame
    - get_history(codes, params) -> DataFrame
    - get_stocks(codes, params) -> DataFrame
    - get_finance_info(codes, params) -> DataFrame
    - get_xdxr(codes, params) -> DataFrame
    - get_index_bars(codes, params) -> DataFrame
    """
```

**并发保护**:
- 使用 `asyncio.Lock()` 保护初始化和关闭操作
- 使用 `asynccontextmanager` 实现客户端租借机制

---

### 3.2 TDXClientPool

**文件**: `src/core/tdx_pool.py`

TDX 多节点连接池，实现负载均衡和故障切换。

**关键特性**:
- 支持多个 TDX 服务器节点
- 连接自动重连机制
- 健康检查和故障剔除
- 信号量控制并发数

---

### 3.3 RedisStreamWorker

**文件**: `src/workers/stream_worker.py`

Redis Stream 请求消费者，支持批量数据请求的异步处理。

---

## 4. 配置

### 4.1 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TDX_POOL_SIZE` | `3` | TDX 连接池大小 |
| `SOCKS_PROXY` | - | SOCKS5 代理 (格式: `host:port`) |
| `REDIS_HOST` | `127.0.0.1` | Redis 地址 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `REDIS_PASSWORD` | - | Redis 密码 |

### 4.2 Monkeypatch

服务启动时会自动执行以下 Monkeypatch:

1. **pytdx 替换 tdxpy**: 使用 `pytdx.hq.TdxHq_API` 替换 `tdxpy.hq.TdxHq_API`，解决连接兼容性问题
2. **SOCKS5 代理**: 如果设置 `SOCKS_PROXY`，全局 socket 将使用 SOCKS5 代理

---

## 5. 健康检查

```
GET /health
```

**响应示例**:
```json
{
  "status": "healthy",
  "service": "mootdx-api",
  "pool": {
    "initialized": true,
    "size": 3,
    "available": 2,
    "active": 1
  },
  "worker": "running"
}
```

---

## 6. 部署

### 6.1 Docker 运行

```bash
docker build -t mootdx-api .
docker run -p 8003:8003 \
  -e TDX_POOL_SIZE=3 \
  -e REDIS_HOST=host.docker.internal \
  mootdx-api
```

### 6.2 本地开发

```bash
cd services/mootdx-api
pip install -r requirements.txt
python src/main.py
```

---

## 7. 依赖服务

| 服务 | 用途 | 必需 |
|------|------|------|
| TDX 服务器 | 数据源 | ✅ |
| Redis | Stream 请求消费 | ❌ |

---

## 8. 错误处理

| HTTP 状态码 | 场景 |
|------------|------|
| 400 | 参数缺失或格式错误 |
| 500 | TDX 连接失败或数据获取异常 |
| 503 | 服务未初始化完成 |

---

## 9. 相关文档

| 文档 | 路径 |
|------|------|
| TDX 连接池文档 | `docs/TDX_CONNECTION_POOL.md` |
| 采集策略与并发指南 | `../../gsd-worker/docs/TICK_ACQUISITION_STRATEGY_AND_CONCURRENCY.md` |
| TDX 节点列表 | `tdx_ip.md` |
| 诊断工具 | `diagnostics/` |
| 连接池测试 | `tests/` |
