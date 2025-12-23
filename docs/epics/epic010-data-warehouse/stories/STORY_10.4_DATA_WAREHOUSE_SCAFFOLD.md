# Story 10.4: data-warehouse 服务脚手架

## Story 信息

| 字段 | 值 |
|------|-----|
| **Story ID** | 10.4 |
| **所属 Epic** | EPIC-010 本地数据仓库 |
| **优先级** | P1 |
| **预估工时** | 3 天 |
| **前置依赖** | Story 10.1 |

---

## 目标

创建 `data-warehouse` 微服务，提供统一数据访问层，供 `quant-strategy` 等消费者使用。

---

## 验收标准

1. ✅ 服务可通过 `docker compose up` 启动
2. ✅ 健康检查接口 `GET /health` 返回 200
3. ✅ 可连接 ClickHouse、Redis、PostgreSQL
4. ✅ 可通过 Nacos 注册发现
5. ✅ Swagger 文档可用

---

## 任务分解

### Task 1: 创建服务目录结构

```
services/data-warehouse/
├── src/
│   ├── main.py
│   ├── api/
│   │   └── routes/
│   ├── services/
│   ├── storage/
│   └── config/
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### Task 2: 存储客户端

```python
# src/storage/clickhouse.py
class ClickHouseClient:
    async def execute(self, query: str, params: dict = None):
        pass

# src/storage/redis_cache.py
class RedisCache:
    async def get(self, key: str):
        pass
    async def set(self, key: str, value: any, ttl: int = 300):
        pass
```

### Task 3: 配置管理

```python
# src/config/settings.py
class Settings(BaseSettings):
    clickhouse_host: str = "microservice-stock-clickhouse"
    redis_host: str = "microservice-stock-redis"
    nacos_server: str = "nacos:8848"
```

---

*创建日期: 2025-12-23*
