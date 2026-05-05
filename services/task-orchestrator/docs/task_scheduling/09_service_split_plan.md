# Phase 3: 服务拆分详细方案

> **版本**: v1.0  
> **创建时间**: 2026-01-02  
> **状态**: 待审阅

---

## 1. 拆分策略总览

### 1.1 目标

从 `get-stockdata` 拆分出：
- **gsd-api**: 长驻查询服务
- **gsd-worker**: 临时任务执行器

同时保留 `get-stockdata` 作为兼容层。

### 1.2 拆分原则

| 原则 | 说明 |
|:-----|:-----|
| **按职责分离** | API查询 vs 数据处理 |
| **运行时独立** | 两者无运行时耦合 |
| **数据模型统一** | 都使用 gsd-shared |
| **渐进式迁移** | 不破坏现有服务 |

---

## 2. 代码分配清单

### 2.1 gsd-api (查询服务)

**核心职责**: 对外提供数据查询 API

#### API Routes (保留)
```
src/api/
├── quotes_routes.py          ✅ → gsd-api
├── kline_routes.py           ✅ → gsd-api (需新建，当前在 main.py)
├── market_routes.py          ✅ → gsd-api
├── stocks_routes.py          ✅ → gsd-api
├── valuation_routes.py       ✅ → gsd-api
├── finance_routes.py         ✅ → gsd-api
├── liquidity_routes.py       ✅ → gsd-api
├── health_routes.py          ✅ → gsd-api
└── routers/
    ├── stock_pool.py         ✅ → gsd-api
    ├── metrics.py            ✅ → gsd-api
    └── config.py             ✅ → gsd-api
```

#### Data Access (只读)
```
src/data_access/
├── kline_dao.py              ✅ → gsd-api (ClickHouse 查询)
├── redis_pool.py             ✅ → gsd-api
└── (其他查询相关)
```

#### Core Services (只读)
```
src/core/
├── quotes_service.py         ✅ → gsd-api
├── statistics_generator.py   ✅ → gsd-api
└── (其他查询服务)
```

#### 依赖
- gsd-shared
- ClickHouse (只读)
- Redis (缓存)  
- 可选: mootdx-source (gRPC,行情)

---

### 2.2 gsd-worker (任务执行器)

**核心职责**: 数据同步、质量检测、修复

#### API Routes (任务触发端点)
```
src/api/
├── sync_routes.py            ✅ → gsd-worker
├── quality_routes.py         ✅ → gsd-worker
└── repair_routes.py          ✅ → gsd-worker
```

#### Core Services (写入+处理)
```
src/core/
├── sync_service.py           ✅ → gsd-worker (K线同步核心)
├── data_quality_service.py   ✅ → gsd-worker (质量检测)
├── data_quality_evaluator.py ✅ → gsd-worker
├── consistency/              ✅ → gsd-worker
│   └── consistency_checker.py
└── recorder/                 ✅ → gsd-worker (记录器)
    └── snapshot_recorder.py
```

#### Data Access (读写)
```
src/data_access/
├── (同 gsd-api，但需要写权限)
└── 新增: 需要 MySQL 连接池
```

#### 依赖
- gsd-shared
- MySQL (读取源数据)
- ClickHouse (写入)
- Redis (锁+状态)

---

### 2.3 共享组件 (两边都需要)

#### Models
```
src/models/
├── base_models.py            ⚠️ 迁移到 gsd-shared
├── stock_models.py           ⚠️ 迁移到 gsd-shared
└── (其他)                    ⚠️ 根据使用情况决定
```

#### Config
```
src/config/
├── settings.py               🔄 两边各自维护
└── (其他配置)
```

#### Utils
```
src/utils/
└── (工具函数)                🔄 按需复制或抽取到 gsd-shared
```

---

## 3. 详细实施步骤

### Step 1: 创建 gsd-api 骨架

```bash
mkdir -p services/gsd-api/src/{api,core,data_access,models,config}
```

#### 1.1 复制查询相关文件

```bash
# API routes
cp services/get-stockdata/src/api/quotes_routes.py services/gsd-api/src/api/
cp services/get-stockdata/src/api/market_routes.py services/gsd-api/src/api/
# ... (其他查询路由)

# Data access
cp services/get-stockdata/src/data_access/kline_dao.py services/gsd-api/src/data_access/
cp services/get-stockdata/src/data_access/redis_pool.py services/gsd-api/src/data_access/
```

#### 1.2 创建 main.py

```python
# services/gsd-api/src/main.py
from fastapi import FastAPI
from gsd_shared.models import KLineRecord  # 使用共享模型

app = FastAPI(title="GSD-API")

# 注册路由
from api import quotes_routes, market_routes, kline_routes
app.include_router(quotes_routes.router)
app.include_router(market_routes.router)
app.include_router(kline_routes.router)
```

#### 1.3 修改导入

将所有 `from models.stock_models import StockInfo` 改为:
```python
from gsd_shared.models import StockInfo
```

---

### Step 2: 创建 gsd-worker 骨架

```bash
mkdir -p services/gsd-worker/src/{jobs,core,data_access}
```

#### 2.1 复制同步相关文件

```bash
# Core services
cp services/get-stockdata/src/core/sync_service.py services/gsd-worker/src/core/
cp services/get-stockdata/src/core/data_quality_service.py services/gsd-worker/src/core/
```

#### 2.2 创建任务入口

```python
# services/gsd-worker/src/jobs/sync_kline.py
"""K线同步任务入口 - 供 task-orchestrator 调用"""
import sys
import asyncio
from gsd_shared.models import KLineRecord
from core.sync_service import KLineSyncService

async def main():
    service = KLineSyncService()
    await service.initialize()
    try:
        await service.sync_smart_incremental()
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(main())
```

#### 2.3 创建 Dockerfile

```dockerfile
# services/gsd-worker/Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 gsd-shared
COPY ../../libs/gsd-shared /tmp/gsd-shared
RUN pip install -e /tmp/gsd-shared

COPY src/ ./src/
ENTRYPOINT ["python", "-m"]
CMD ["jobs.sync_kline"]  # 默认执行同步任务
```

---

### Step 3: 更新配置

#### 3.1 gsd-api pyproject.toml

```toml
[project]
dependencies = [
    "fastapi>=0.104.1",
    "gsd-shared @ file:///${PROJECT_ROOT}/../../libs/gsd-shared",
    # ... (只读依赖)
]
```

#### 3.2 gsd-worker pyproject.toml

```toml
[project]
dependencies = [
    "gsd-shared @ file:///${PROJECT_ROOT}/../../libs/gsd-shared",
    "aiomysql",
    "asynch",  # ClickHouse async
    # ... (读写依赖)
]
```

---

### Step 4: Docker Compose 配置

#### 4.1 docker-compose.gsd.yml

```yaml
services:
  gsd-api:
    build: ./services/gsd-api
    ports:
      - "8001:8000"
    environment:
      - CLICKHOUSE_HOST=clickhouse
      - REDIS_HOST=redis
    depends_on:
      - clickhouse
      - redis

  # gsd-worker 不在此启动，由 task-orchestrator 管理
```

---

## 4. 代码迁移核心问题

### 4.1 数据模型替换

#### 问题
get-stockdata 使用自己的 `models/stock_models.py`，需要替换为 gsd-shared。

#### 解决方案
**方案 A**: 全量替换
```python
# 全局搜索替换
from models.stock_models import StockInfo
↓
from gsd_shared.models import StockInfo
```

**方案 B**: 兼容层（推荐）
```python
# get-stockdata/src/models/stock_models.py (保留文件)
from gsd_shared.models import StockInfo as _StockInfo, StockCodeMapping as _StockCodeMapping

# 暴露相同接口
StockInfo = _StockInfo
StockCodeMapping = _StockCodeMapping
```

### 4.2 配置管理

#### 问题
三个服务的配置如何管理？

#### 解决方案
```
services/
├── gsd-api/.env.example
├── gsd-worker/.env.example
└── get-stockdata/.env (保留现有)
```

共享配置通过环境变量注入:
- `CLICKHOUSE_HOST`
- `REDIS_HOST`
- `MYSQL_HOST` (worker专用)

---

## 5. 验证计划

### 5.1 gsd-api 验证

```bash
# 启动服务
docker compose -f docker-compose.gsd.yml up gsd-api

# 测试查询接口
curl http://localhost:8001/api/v1/quotes/realtime/000001
curl http://localhost:8001/api/v1/kline/daily/000001
```

### 5.2 gsd-worker 验证

```bash
# 手动运行同步任务
docker run --rm --network host gsd-worker python -m jobs.sync_kline

# 检查 ClickHouse 数据
clickhouse-client -q "SELECT COUNT(*) FROM stock_kline_daily"
```

---

## 6. 风险与缓解

| 风险 | 影响 | 缓解 |
|:-----|:-----|:-----|
| 模型不兼容 | 运行时报错 | 充分测试，使用 Pydantic 校验 |
| 配置遗漏 | 服务启动失败 | 使用 `.env.example` 模板 |
| 依赖冲突 | pip安装失败 | 独立 pyproject.toml |
| 数据不一致 | gsd-api 查不到 worker 写入的数据 | 统一使用 gsd-shared 模型 |

---

## 7. 时间估算

| 步骤 | 时间 | 备注 |
|:-----|:-----|:-----|
| Step 1: gsd-api 骨架 | 2小时 | 复制+修改导入 |
| Step 2: gsd-worker 骨架 | 2小时 | 创建job入口 |
| Step 3: 配置文件 | 1小时 | pyproject.toml, Dockerfile |
| Step 4: 测试验证 | 2小时 | 端到端测试 |
| **总计** | **7小时** | 约1个工作日 |

---

## 8. 待确认事项

> [!IMPORTANT]
> 请确认以下决策：

1. **数据模型迁移方案**: 全量替换 or 兼容层？（推荐方案B）
2. **get-stockdata 保留多久**: 新服务稳定后立即废弃 or 保留3个月？
3. **并行运行**: 拆分期间，新旧服务是否并行运行？
4. **分片参数**: gsd-worker 的 `--shard` 参数如何传递？（通过命令行 or 环境变量）

---

## 附录: 文件清单

### gsd-api 需要的文件 (共 ~30个)
- src/api/: 10个路由文件
- src/core/: 5个服务文件
- src/data_access/: 3个DAO文件
- src/models/: 使用 gsd-shared
- src/config/, src/utils/

### gsd-worker 需要的文件 (共 ~15个)
- src/jobs/: 3个任务入口
- src/core/: sync_service, quality_service, recorder
- src/data_access/: 共享 DAO
- src/config/
