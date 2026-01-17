# microservice-stock 微服务规格说明书

> **版本**: v1.0  
> **更新时间**: 2026-01-17  
> **目标市场**: A股市场 (中国沪深交易所)  
> **时区**: Asia/Shanghai (CST)

---

## 1. 系统概述

**microservice-stock** 是一个基于事件驱动架构的 A 股数据采集与量化分析微服务系统，支持实时数据处理、分布式任务调度和策略回测。

### 1.1 核心能力

| 能力领域 | 描述 |
|---------|------|
| 数据采集 | 通达信(TDX)实时行情、分笔数据、K线历史 |
| 分布式存储 | ClickHouse 3分片集群 + Redis 3节点 Cluster |
| 任务调度 | APScheduler 定时任务 + 交易日历感知 |
| 量化策略 | OFI、Smart Money、VWAP 等策略引擎 |
| 数据质量 | 盘前/盘后质量门禁 + 自动修复机制 |

### 1.2 技术栈

- **语言**: Python 3.12+
- **Web框架**: FastAPI
- **并发模型**: Asyncio
- **数据处理**: Pandas, Numpy
- **存储**: ClickHouse (Tick/K线), Redis (缓存/锁), MySQL (元数据)
- **部署**: Docker, Docker Compose
- **服务注册**: Nacos (可选)

---

## 2. 服务清单

### 2.1 核心服务

| 服务名 | 端口 | 职责 | 状态 |
|--------|------|------|------|
| `mootdx-api` | 8003 | 通达信数据源 REST API 网关 | ✅ 生产 |
| `gsd-worker` | - | 数据采集任务执行器 (K线/Tick/元数据) | ✅ 生产 |
| `task-orchestrator` | 18000 | 任务调度中心 (Cron/DAG) | ✅ 生产 |
| `gsd-api` | 8000 | 股票数据只读查询 API | ✅ 生产 |
| `quant-strategy` | 8084 | 量化策略引擎 | 🔄 开发中 |

### 2.2 辅助服务

| 服务名 | 职责 | 状态 |
|--------|------|------|
| `monitoring-exporter` | Prometheus 指标导出 | ✅ 生产 |
| `mootdx-source` | TDX 数据源备用服务 | ⏸️ 备用 |
| `stock-data` | 股票数据服务 (旧版) | ⏸️ 废弃 |

---

## 3. 服务详细规格

> **📚 详细文档**: 每个服务都有独立的详细规格文档，位于各服务的 `docs/SERVICE_SPEC.md`：
> 
> | 服务 | 详细文档 |
> |------|----------|
> | mootdx-api | [services/mootdx-api/docs/SERVICE_SPEC.md](../services/mootdx-api/docs/SERVICE_SPEC.md) |
> | gsd-worker | [services/gsd-worker/docs/SERVICE_SPEC.md](../services/gsd-worker/docs/SERVICE_SPEC.md) |
> | task-orchestrator | [services/task-orchestrator/docs/SERVICE_SPEC.md](../services/task-orchestrator/docs/SERVICE_SPEC.md) |
> | gsd-api | [services/gsd-api/docs/SERVICE_SPEC.md](../services/gsd-api/docs/SERVICE_SPEC.md) |
> | quant-strategy | [services/quant-strategy/docs/SERVICE_SPEC.md](../services/quant-strategy/docs/SERVICE_SPEC.md) |

### 3.1 mootdx-api (通达信数据源网关)

**职责**: 封装 mootdx 库，提供 TDX 数据的 HTTP REST 接口。

#### API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/quotes?codes=` | 实时行情 (支持批量) |
| GET | `/api/v1/tick/{code}` | 分笔成交 (支持历史日期) |
| GET | `/api/v1/history/{code}` | 历史K线 (日/周/月) |
| GET | `/api/v1/stocks` | 股票列表 (全市场) |
| GET | `/api/v1/finance/{code}` | 财务基础信息 |
| GET | `/api/v1/xdxr/{code}` | 除权除息数据 |
| GET | `/api/v1/index/bars/{code}` | 指数K线 |

#### 核心组件

| 组件 | 文件 | 功能 |
|------|------|------|
| `MootdxHandler` | `handlers/mootdx_handler.py` | TDX 连接池管理 + 数据获取 |
| `TDXClientPool` | `core/tdx_pool.py` | 多节点连接池负载均衡 |
| `RedisStreamWorker` | `workers/stream_worker.py` | Redis Stream 请求消费 |

#### 连接池配置

```yaml
TDX_POOL_SIZE: 3  # 连接池大小 (环境变量)
SOCKS_PROXY: ""   # 可选 SOCKS5 代理
```

---

### 3.2 gsd-worker (数据采集执行器)

**职责**: 执行各类数据采集、同步、质量检测任务。

#### 任务清单

| 任务 | 入口 | 触发方式 | 描述 |
|------|------|---------|------|
| `daily_stock_collection` | `jobs/daily_stock_collection.py` | Cron 08:45 | 每日股票代码采集 + 分片计算 |
| `sync_kline` | `jobs/sync_kline.py` | Cron 17:30 | K线每日同步 |
| `sync_tick` | `jobs/sync_tick.py` | Cron 15:35 | 分笔数据全量采集 |
| `pre_market_gate` | `jobs/pre_market_gate.py` | Cron 09:15 | 盘前数据质量门禁 |
| `post_market_gate` | `jobs/post_market_gate.py` | Cron 19:18 | 盘后数据质量审计 |
| `quality_check` | `jobs/quality_check.py` | 手动/依赖 | 数据质量检测 |
| `retry_tick` | `jobs/retry_tick.py` | 自动补采 | 分笔数据失败重试 |
| `supplement_stock` | `jobs/supplement_stock.py` | API触发 | 定向个股数据补充 |

#### 核心服务

| 服务 | 文件 | 功能 |
|------|------|------|
| `SyncService` | `core/sync_service.py` | K线同步核心逻辑 |
| `TickSyncService` | `core/tick_sync_service.py` | 分笔数据采集 |
| `PostMarketGateService` | `core/post_market_gate_service.py` | 盘后审计 + 自动修复 |
| `PreMarketGateService` | `core/pre_market_gate_service.py` | 盘前准入检查 |
| `SupplementEngine` | `core/supplement_engine.py` | 定向数据补充引擎 |
| `DataQualityService` | `core/data_quality_service.py` | 数据质量评估 |

#### 依赖

- MySQL (源数据/元数据)
- ClickHouse (目标存储)
- Redis (锁/状态/缓存)
- mootdx-api (TDX 数据接口)

---

### 3.3 task-orchestrator (任务调度中心)

**职责**: 集中管理定时任务，支持交易日历感知调度。

#### 任务类型

| 类型 | 描述 | 示例 |
|------|------|------|
| `docker` | 启动 Docker 容器执行命令 | K线同步 |
| `http` | 发送 HTTP 请求 (Webhook/API) | 缓存预热 |
| `workflow` | 串行/并行执行子任务 (DAG) | 分笔采集+补采 |

#### 调度类型

| 类型 | 描述 |
|------|------|
| `cron` | 标准 Cron 表达式 |
| `trading_cron` | 仅在 A 股交易日触发 |

#### 关键配置 (`config/tasks.yml`)

| 任务ID | 时间 | 类型 | 描述 |
|--------|------|------|------|
| `daily_stock_collection` | 08:45 | docker | 股票代码采集 |
| `daily_kline_sync` | 17:30 | docker | K线每日同步 |
| `pre_market_gate` | 09:15 | docker | 盘前质量门禁 |
| `post_market_gate` | 19:18 | docker | 盘后审计门禁 |
| `daily_cache_warmup` | 09:20 | http | 缓存预热 |
| `tick_data_migrate` | 09:00 | http | 分笔数据归档 |

#### API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/jobs` | 列出所有调度任务 |
| GET | `/api/v1/tasks/` | 任务管理 API |

---

### 3.4 gsd-api (数据查询服务)

**职责**: 提供股票数据的只读查询接口。

#### API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/quotes` | 实时行情查询 |
| GET | `/api/v1/kline` | K线数据查询 |
| GET | `/api/v1/market` | 市场数据查询 |
| GET | `/api/v1/stocks` | 股票列表查询 |
| GET | `/api/v1/finance` | 财务数据查询 |

#### 数据源

- ClickHouse (主查询)
- Redis (缓存层)

---

### 3.5 quant-strategy (量化策略引擎)

**职责**: 提供策略管理、信号生成与回测功能。

#### 支持策略

| 策略代码 | 名称 | 描述 |
|---------|------|------|
| `ofi` | 订单流失衡策略 | Order Flow Imbalance 分析 |
| `smart_money` | 大单资金追踪 | 识别主力资金行为 |
| `order_book` | 盘口压力分析 | 五档委买委卖压力差 |
| `vwap` | VWAP 乖离策略 | 基于 VWAP 的均值回归 |
| `liquidity_shock` | 流动性冲击监控 | 交易冲击成本检测 |

#### API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/strategies/` | 获取策略列表 |
| GET | `/api/v1/strategies/{id}` | 获取策略详情 |
| POST | `/api/v1/strategies/` | 创建策略 |
| POST | `/api/v1/strategies/{id}/backtest` | 回测策略 |
| GET | `/api/v1/strategies/{id}/signals` | 获取策略信号 |

---

## 4. 基础设施架构

### 4.1 分布式存储 (3-Shard 架构)

```
┌─────────────────────────────────────────────────────────┐
│                    客户端/应用                           │
│                         │                               │
│            ┌────────────┴────────────┐                  │
│            ▼                         ▼                  │
│    ClickHouse 分布式表         Redis Cluster            │
│            │                         │                  │
│   ┌────────┼────────┐       ┌────────┼────────┐        │
│   ▼        ▼        ▼       ▼        ▼        ▼        │
│ Shard1   Shard2   Shard3  Master1  Master2  Master3    │
│ (41)     (58)     (111)   (41)     (58)     (111)      │
└─────────────────────────────────────────────────────────┘
```

### 4.2 ClickHouse 配置

| 参数 | 值 |
|------|-----|
| 分片数 | 3 (Server 41/58/111) |
| 副本数 | 无 (纯分片模式) |
| 分片键 | `cityHash64(stock_code)` |
| 端口 | 9000 (Native), 8123 (HTTP) |

### 4.3 Redis Cluster 配置

| 参数 | 值 |
|------|-----|
| 节点数 | 3 Master |
| 端口 | 16379 |
| Slots | 0-5460 / 5461-10922 / 10923-16383 |

---

## 5. 数据流

### 5.1 K线数据流

```
[mootdx-api] → [gsd-worker:sync_kline] → [ClickHouse:stock_kline_daily]
       ↑
  TDX服务器
```

### 5.2 分笔数据流

```
[mootdx-api] → [gsd-worker:sync_tick] → [Redis Stream] → [ClickHouse:tick_data]
       ↑
  TDX服务器
```

### 5.3 策略信号流

```
[ClickHouse] → [quant-strategy] → [Redis:signals] → [通知/交易]
```

---

## 6. 调度时间表

| 时间 | 任务 | 优先级 |
|------|------|--------|
| 08:45 | 股票代码采集 | P0 |
| 09:00 | 分笔数据归档 | P0 |
| 09:15 | 盘前质量门禁 | P0 |
| 09:20 | 缓存预热 | P1 |
| 15:35 | 盘后分笔采集 | P1 |
| 17:30 | K线每日同步 | P0 |
| 18:30 | 策略扫描 | P1 |
| 19:18 | 盘后审计门禁 | P0 |

---

## 7. 环境变量

### 通用配置

| 变量 | 描述 | 示例 |
|------|------|------|
| `REDIS_HOST` | Redis 地址 | `127.0.0.1` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `REDIS_PASSWORD` | Redis 密码 | `redis123` |
| `CLICKHOUSE_HOST` | ClickHouse 地址 | `127.0.0.1` |
| `MYSQL_HOST` | MySQL 地址 | `127.0.0.1` |

### mootdx-api 专用

| 变量 | 描述 | 示例 |
|------|------|------|
| `TDX_POOL_SIZE` | TDX 连接池大小 | `3` |
| `SOCKS_PROXY` | SOCKS5 代理 | `127.0.0.1:1080` |

### gsd-worker 专用

| 变量 | 描述 | 示例 |
|------|------|------|
| `MOOTDX_API_URL` | mootdx-api 地址 | `http://mootdx-api:8003` |
| `KLINE_THRESHOLD` | K线覆盖率阈值 | `98` |
| `TICK_THRESHOLD` | 分笔覆盖率阈值 | `95` |

---

## 8. 部署模式

### 8.1 单节点开发

```bash
docker-compose -f docker-compose.yml up -d
```

### 8.2 三节点生产

```bash
# Server 41 (主节点)
docker-compose -f docker-compose.node-41.yml up -d

# Server 58
docker-compose -f docker-compose.node-58.yml up -d

# Server 111
docker-compose -f docker-compose.node-111.yml up -d
```

---

## 9. 相关文档

| 文档 | 路径 |
|------|------|
| 架构概览 | `docs/architecture/index.md` |
| ClickHouse 集群 | `docs/architecture/infrastructure/clickhouse-3shard-cluster.md` |
| Redis 集群 | `docs/architecture/infrastructure/redis-3shard-cluster.md` |
| 分笔数据分片 | `docs/architecture/tick_data_sharding_implementation.md` |
| 数据质量门禁 | `services/task-orchestrator/docs/data_gates/` |
| 任务配置 | `services/task-orchestrator/config/tasks.yml` |
