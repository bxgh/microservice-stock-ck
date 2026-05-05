# EPIC-010 技术架构设计

## 文档信息
| 字段 | 值 |
|------|-----|
| **所属 EPIC** | EPIC-010 本地数据仓库 |
| **文档类型** | 技术架构设计 |
| **创建日期** | 2025-12-23 |
| **版本** | 1.0 |

---

## 1. 架构总览

```
                          ┌─────────────────────────────────────┐
                          │          真实数据源 (外部)            │
                          │  ┌─────────┐ ┌─────────┐ ┌─────────┐ │
                          │  │Baostock │ │ AkShare │ │ Mootdx  │ │
                          │  └────┬────┘ └────┬────┘ └────┬────┘ │
                          └───────┼───────────┼───────────┼──────┘
                                  │           │           │
                                  ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    data-collector 服务 (新建)                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    数据采集引擎                            │   │
│  │  • 定时任务: 日K线、财务、估值                            │   │
│  │  • 实时采集: 分笔数据 (交易时间)                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│              ┌───────────────┼───────────────┐                   │
│              ▼               ▼               ▼                   │
│       本地 ClickHouse    腾讯云 MySQL     本地 Redis             │
│        (主存储)           (云端备份)       (实时缓存)             │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       本地存储层                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  ClickHouse  │  │    Redis     │  │  PostgreSQL  │           │
│  │  (时序数据)   │  │   (缓存)     │  │  (元数据)    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ 统一数据访问
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    data-warehouse 服务                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    统一数据访问 API                        │   │
│  │  • REST API: /api/v1/data/...                            │   │
│  │  • gRPC (可选): 高性能内部通信                            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
              ┌───────────────┼───────────────┐
              │               │               │
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│quant-strategy│  │get-stockdata │  │task-scheduler│
└──────────────┘  └──────────────┘  └──────────────┘
              数据消费者
```

### 数据流说明

| 流向 | 说明 |
|------|------|
| **① 采集** | `data-collector` 从真实数据源 (Baostock/AkShare/Mootdx) 抓取数据 |
| **② 存储** | 采集后数据写入本地 ClickHouse (主) 和腾讯云 MySQL (备份) |
| **③ 访问** | `data-warehouse` 提供统一查询 API，消费者通过它访问数据 |

---

## 2. 核心模块设计

### 2.1 data-collector 服务结构 (新建)

**职责**: 从真实数据源采集数据，写入本地存储和云端备份

```
services/data-collector/
├── src/
│   ├── main.py               # 入口
│   ├── collectors/
│   │   ├── baostock.py       # Baostock 采集器
│   │   ├── akshare.py        # AkShare 采集器
│   │   └── mootdx.py         # Mootdx 采集器
│   ├── writers/
│   │   ├── clickhouse.py     # ClickHouse 写入
│   │   ├── mysql_cloud.py    # 腾讯云 MySQL 写入
│   │   └── redis.py          # Redis 实时缓存
│   ├── scheduler/
│   │   └── jobs.py           # 定时任务定义
│   └── config/
│       └── settings.py
└── docker-compose.yml
```

### 2.2 data-warehouse 服务结构

```
services/data-warehouse/
├── src/
│   ├── main.py               # 入口
│   ├── api/
│   │   ├── routes/
│   │   │   ├── kline.py      # K线数据接口
│   │   │   ├── financials.py # 财务数据接口
│   │   │   ├── factors.py    # 因子数据接口
│   │   │   └── sync.py       # 同步任务接口
│   ├── services/
│   │   ├── query_engine.py   # 查询引擎
│   │   ├── sync_engine.py    # 同步引擎
│   │   └── factor_engine.py  # 因子计算引擎
│   ├── storage/
│   │   ├── clickhouse.py     # ClickHouse 客户端
│   │   ├── redis_cache.py    # Redis 缓存
│   │   └── postgres.py       # PostgreSQL 客户端
│   └── sync/
│       ├── mysql_sync.py     # 云端 MySQL 同步
│       └── api_sync.py       # 外部 API 同步
└── docker-compose.yml
```

### 2.2 同步引擎设计

```python
class SyncEngine:
    """数据同步引擎"""
    
    async def sync_financials_from_cloud(self) -> SyncResult:
        """从腾讯云 MySQL 同步财务数据"""
        pass
    
    async def sync_kline_daily(self) -> SyncResult:
        """从 Baostock 同步日K线"""
        pass
    
    async def sync_valuation(self) -> SyncResult:
        """从 AkShare 同步估值数据"""
        pass
```

---

## 3. 技术选型

| 组件 | 技术选择 | 理由 |
|------|----------|------|
| 时序存储 | ClickHouse | 已部署，高性能时序查询 |
| 缓存 | Redis | 已部署，毫秒级响应 |
| 元数据 | PostgreSQL | 关系型数据，事务支持 |
| 服务框架 | FastAPI | 与现有服务一致 |
| 任务调度 | APScheduler | 轻量级，易集成 |
| 云端同步 | aiomysql | 异步 MySQL 客户端 |

---

## 4. 接口设计

### 4.1 K线数据接口

```
GET /api/v1/data/kline/daily
参数:
  - codes: list[str]  # 股票代码列表
  - start: date       # 开始日期
  - end: date         # 结束日期
  
响应:
{
  "success": true,
  "data": {
    "600519": [
      {"date": "2025-12-20", "open": 1800.0, "close": 1850.0, ...}
    ]
  }
}
```

### 4.2 财务数据接口

```
GET /api/v1/data/financials/{code}
参数:
  - periods: int = 8  # 返回近 N 期
  
响应:
{
  "success": true,
  "data": [
    {"report_date": "2025-09-30", "revenue": 100000, "net_profit": 50000, ...}
  ]
}
```

### 4.3 因子数据接口

```
GET /api/v1/data/factors/{factor_id}
参数:
  - codes: list[str]  # 股票代码列表
  - date: date        # 日期
  
响应:
{
  "success": true,
  "data": {
    "600519": 85.5,
    "000001": 72.3
  }
}
```

---

## 5. 部署拓扑

```yaml
# docker-compose 新增服务
services:
  data-warehouse:
    build: ./services/data-warehouse
    ports:
      - "8088:8088"
    environment:
      - CLICKHOUSE_HOST=microservice-stock-clickhouse
      - REDIS_HOST=microservice-stock-redis
      - CLOUD_MYSQL_HOST=${TENCENT_MYSQL_HOST}
    depends_on:
      - clickhouse
      - redis
    networks:
      - microservice-stock
```

---

*文档版本: 1.0*  
*最后更新: 2025-12-23*
