# Story 10.0: data-collector 服务脚手架

## Story 信息

| 字段 | 值 |
|------|-----|
| **Story ID** | 10.0 |
| **所属 Epic** | EPIC-010 本地数据仓库 |
| **优先级** | P0 |
| **预估工时** | 3 天 |
| **前置依赖** | 无 |

---

## 目标

创建 `data-collector` 微服务的基础框架，为后续采集任务提供调度和执行环境。

---

## 验收标准

1. ✅ 服务可通过 `docker compose up` 启动
2. ✅ 健康检查接口 `GET /health` 返回 200
3. ✅ APScheduler 调度器正常运行
4. ✅ 可通过 Nacos 注册发现
5. ✅ 日志输出正常

---

## 任务分解

### Task 1: 创建服务目录结构
```
services/data-collector/
├── src/
│   ├── main.py
│   ├── api/
│   ├── collectors/
│   ├── writers/
│   ├── scheduler/
│   └── config/
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### Task 2: 实现 FastAPI 入口

```python
# src/main.py
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

app = FastAPI(title="Data Collector", version="1.0.0")
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup():
    scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()

@app.get("/health")
async def health():
    return {"status": "healthy", "scheduler": "running"}
```

### Task 3: 配置 Docker 和依赖

**requirements.txt**:
```
fastapi>=0.104.0
uvicorn>=0.24.0
apscheduler>=3.10.0
aiomysql>=0.2.0
clickhouse-driver>=0.2.6
redis>=5.0.0
nacos-sdk-python>=0.1.13
```

### Task 4: Nacos 注册

```python
# src/config/nacos.py
async def register_to_nacos():
    # 实现 Nacos 服务注册
    pass
```

---

## 技术说明

- **调度器**: APScheduler AsyncIO 模式
- **运行端口**: 8089
- **日志格式**: 与现有服务一致

---

*创建日期: 2025-12-23*
