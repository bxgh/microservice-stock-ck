# task-orchestrator 服务规格说明

> **版本**: v1.0  
> **更新时间**: 2026-01-17  
> **服务端口**: 18000  
> **状态**: ✅ 生产环境

---

## 1. 服务概述

`task-orchestrator` 是系统的任务调度中心，基于 APScheduler 实现，负责整个系统的任务调度与协调，支持交易日历感知、Docker 容器任务、HTTP 请求任务以及复杂的工作流 (DAG)。

### 1.1 核心职责

| 职责 | 描述 |
|------|------|
| 统一调度 | 集中管理所有定时任务 (Cron/Interval/Date) |
| 交易日历 | 支持 `trading_cron` 类型，仅在 A 股交易日触发 |
| 任务执行 | Docker 容器任务、HTTP 请求、Workflow DAG |
| 失败重试 | 内置指数退避重试机制 |
| 日志记录 | 任务执行结果记录到 MySQL |

### 1.2 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 调度器 | APScheduler (AsyncIOScheduler) |
| 容器执行 | Docker SDK (aiodocker) |
| 数据库 | MySQL (执行日志) |
| 监控 | Prometheus (/metrics) |

---

## 2. 任务类型

### 2.1 docker 类型

启动 Docker 容器执行命令，任务完成后容器自动销毁。

```yaml
- id: daily_kline_sync
  type: docker
  target:
    image: gsd-worker:latest
    command: ["jobs.sync_kline", "--mode", "adaptive"]
    network_mode: host
    environment:
      PYTHONPATH: /app/src
```

**执行逻辑**:
1. 拉取/创建容器
2. 执行命令
3. 等待完成并捕获退出码
4. 记录日志 (含 stdout/stderr)
5. 清理容器

---

### 2.2 http 类型

发送 HTTP 请求，支持 GET/POST 方法。

```yaml
- id: daily_cache_warmup
  type: http
  target:
    url: "http://gsd-api:8000/api/v1/internal/warmup"
    method: POST
    timeout_seconds: 60
```

**用途示例**:
- 缓存预热
- ClickHouse 数据迁移
- Webhook 通知

---

### 2.3 workflow 类型

串行/并行执行一组子任务，支持依赖关系 (DAG)。

```yaml
- id: daily_tick_sync_workflow
  type: workflow
  workflow:
    - id: collect
      name: 分片采集
      command: ["jobs.sync_tick", "--scope", "all"]
    - id: retry
      name: 自动补采
      command: ["jobs.retry_tick"]
      depends_on: [collect]
```

---

## 3. 调度类型

### 3.1 cron

标准 Cron 表达式，每日/每周/每月触发。

```yaml
schedule:
  type: cron
  expression: "30 17 * * *"  # 每日 17:30
```

### 3.2 trading_cron

仅在 A 股交易日触发，自动过滤周末和节假日。

```yaml
schedule:
  type: trading_cron
  expression: "30 17 * * 1-5"  # 每个交易日 17:30
```

**交易日历**:
- 自动识别 A 股休市日 (周末 + 节假日)
- 使用 `exchange_calendars` 库获取交易日历

---

## 4. 任务配置

### 4.1 配置文件

**路径**: `config/tasks.yml`

```yaml
version: "1.0"
timezone: "Asia/Shanghai"

global:
  docker:
    image: gsd-worker:latest
    network_mode: host
    default_volumes:
      - ./libs/gsd-shared:/app/libs/gsd-shared:ro
      - ./services/gsd-worker/config:/app/config:ro
      - ./services/gsd-worker/src:/app/src
    environment:
      PYTHONPATH: /app/src

tasks:
  - id: daily_kline_sync
    name: K线每日同步
    type: docker
    enabled: true
    schedule:
      type: trading_cron
      expression: "30 17 * * *"
    target:
      command: ["jobs.sync_kline", "--mode", "adaptive"]
    retry:
      max_attempts: 2
      backoff_seconds: 600
```

### 4.2 任务定义字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 任务唯一标识 |
| `name` | string | ✅ | 任务显示名称 |
| `type` | enum | ✅ | `docker` / `http` / `workflow` |
| `enabled` | bool | ❌ | 是否启用 (默认 true) |
| `schedule` | object | ✅ | 调度配置 |
| `target` | object | ✅ | 执行目标配置 |
| `retry` | object | ❌ | 重试配置 |
| `dependencies` | list | ❌ | 依赖的任务 ID 列表 |

---

## 5. 当前任务清单

### 5.1 数据同步任务

| 任务 ID | 时间 | 类型 | 说明 |
|---------|------|------|------|
| `daily_stock_collection` | 08:45 | docker | 股票代码采集 |
| `daily_kline_sync` | 17:30 | docker | K 线同步 |
| `tick_data_migrate` | 09:00 | http | 分笔数据归档 |

### 5.2 数据质量任务

| 任务 ID | 时间 | 类型 | 说明 |
|---------|------|------|------|
| `pre_market_gate` | 09:15 | docker | 盘前质量门禁 |
| `post_market_gate` | 19:18 | docker | 盘后审计门禁 |

### 5.3 策略任务

| 任务 ID | 时间 | 类型 | 说明 |
|---------|------|------|------|
| `daily_strategy_scan` | 18:30 | docker | 每日策略扫描 |

### 5.4 系统维护

| 任务 ID | 时间 | 类型 | 说明 |
|---------|------|------|------|
| `daily_db_backup` | 03:00 | docker | 数据库备份 |
| `daily_cache_warmup` | 09:20 | http | 缓存预热 |
| `weekly_log_cleanup` | 周日 02:00 | docker | 日志清理 |
| `weekly_clickhouse_log_cleanup` | 周日 03:00 | http | ClickHouse 日志清理 |

### 5.5 手动触发任务

| 任务 ID | 说明 |
|---------|------|
| `repair_kline` | K 线补采 |
| `repair_tick` | 分笔补采 |
| `stock_data_supplement` | 定向个股补充 |

---

## 6. API 接口

### 6.1 健康检查

```
GET /health
```

**响应**:
```json
{
  "status": "healthy",
  "scheduler": "running",
  "jobs_count": 15,
  "mysql": "connected"
}
```

---

### 6.2 列出任务

```
GET /jobs
```

**响应**:
```json
{
  "jobs": [
    {
      "id": "daily_kline_sync",
      "name": "K线每日同步",
      "next_run": "2026-01-17T17:30:00+08:00",
      "trigger": "cron[30 17 * * *]"
    }
  ]
}
```

---

### 6.3 任务管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/tasks/` | 列出所有任务 |
| GET | `/api/v1/tasks/{id}` | 获取任务详情 |
| POST | `/api/v1/tasks/{id}/run` | 手动触发任务 |
| PUT | `/api/v1/tasks/{id}/enable` | 启用任务 |
| PUT | `/api/v1/tasks/{id}/disable` | 禁用任务 |

---

### 6.4 Prometheus 指标

```
GET /metrics
```

**关键指标**:
| 指标 | 类型 | 说明 |
|------|------|------|
| `task_executions_total` | Counter | 任务执行总数 |
| `task_execution_duration_seconds` | Histogram | 任务执行时长 |
| `task_failures_total` | Counter | 任务失败总数 |

---

## 7. 核心组件

### 7.1 GenericTaskRunner

**文件**: `src/main.py`

通用任务执行器，支持三种任务类型。

| 方法 | 说明 |
|------|------|
| `run_http_task(task)` | 执行 HTTP 任务 |
| `run_docker_task(task)` | 执行 Docker 任务 |
| `run_workflow_task(task)` | 执行 Workflow 任务 |

---

### 7.2 TaskConfig

**文件**: `src/config/task_config.py`

任务配置加载器，解析 `tasks.yml`。

---

### 7.3 TaskLogger

**文件**: `src/core/task_logger.py`

任务执行日志记录器，写入 MySQL `task_execution_logs` 表。

---

## 8. 分布式架构

### 8.1 三节点协同

```
┌─────────────────────────────────────────────────────────┐
│                    task-orchestrator                     │
│                    (Server 41, Port 18000)               │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Shard 0 任务  │  │ 全局任务      │  │ 命令分发      │   │
│  │ (本地 Docker) │  │ (K线、门禁)   │  │ (Redis Pub)  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Server 41    │     │  Server 58    │     │  Server 111   │
│  (Shard 0)    │     │  (Shard 1)    │     │  (Shard 2)    │
│  Cron/Docker  │     │  CommandPoller │     │  CommandPoller │
└──────────────┘     └──────────────┘     └──────────────┘
```

### 8.2 远程节点 Poller

**文件**: `src/shard_poller.py`

远程节点 (Server 58/111) 使用 CommandPoller 从 Redis 获取命令并执行。

---

## 9. 配置

### 9.1 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MYSQL_HOST` | - | MySQL 地址 |
| `MYSQL_PORT` | 3306 | MySQL 端口 |
| `MYSQL_USER` | - | MySQL 用户名 |
| `MYSQL_PASSWORD` | - | MySQL 密码 |
| `MYSQL_DATABASE` | task_scheduler | 数据库名 |
| `DOCKER_HOST` | unix:///var/run/docker.sock | Docker 连接地址 |
| `TZ` | Asia/Shanghai | 时区 |

---

## 10. 数据库

### 10.1 表结构

**task_execution_logs**:
```sql
CREATE TABLE task_execution_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    task_name VARCHAR(128),
    status ENUM('started', 'success', 'failed'),
    started_at DATETIME,
    finished_at DATETIME,
    duration_seconds FLOAT,
    records_count INT,
    message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 11. 部署

### 11.1 Docker 运行

```bash
docker-compose up -d task-orchestrator
```

### 11.2 查看调度日志

```bash
docker-compose logs -f task-orchestrator
```

---

## 12. 依赖服务

| 服务 | 用途 | 必需 |
|------|------|------|
| MySQL | 执行日志存储 | ✅ |
| Docker | 容器任务执行 | ✅ |
| Redis | 命令分发 (分布式) | ❌ |

---

## 13. 相关文档

| 文档 | 路径 |
|------|------|
| 任务配置 | `config/tasks.yml` |
| 数据质量门禁 | `docs/data_gates/` |
| 分布式架构 | `../../docs/architecture/tick_data_sharding_implementation.md` |
