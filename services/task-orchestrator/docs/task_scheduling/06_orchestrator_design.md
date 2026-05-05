# Task Orchestrator 详细设计

> **版本**: v1.0  
> **状态**: 规划中  
> **定位**: 整个数据平台的"指挥官"，负责任务调度、容器编排、依赖管理和告警通知。

---

## 1. 核心功能模块

```
task-orchestrator
├── 核心引擎
│   ├── Trigger Engine       # 触发器 (Cron, Calendar, Event)
│   ├── DAG Engine           # 依赖编排 (任务流状态机)
│   └── Executor Engine      # 执行器 (Docker, HTTP)
│
├── 辅助模块
│   ├── Calendar Service     # 交易日历服务
│   ├── Notify Service       # 告警通知
│   └── State Manager        # 状态持久化 (Redis/MySQL)
│
└── 接口层
    ├── REST API             # 管理接口
    └── Dashboard (可选)      # 可视化界面
```

---

## 2. 详细功能规划

### 2.1 智能触发器 (Smart Triggers)

不再是简单的 Crontab，而是**业务感知**的触发器。

| 触发器类型 | 逻辑 | 参数示例 |
|:-----------|:-----|:---------|
| **TradingDayTrigger** | 仅交易日触发 | `time="18:00", offset="0"` (当日) |
| **TradingDayOffsetTrigger** | T+N 交易日触发 | `time="09:00", offset="-1"` (上一交易日) |
| **DataReadyTrigger** | 上游数据就绪触发 | `check_url="/upstream/check", interval="5m"` |
| **EventTrigger** | 收到外部事件触发 | `event_type="market_close"` |

**核心逻辑**:
```python
async def should_fire(self, trigger_context):
    if not await self.calendar.is_trading_day(today):
        return False
    # ... 其他检查
    return True
```

### 2.2 容器执行器 (Docker Executor)

支持**临时任务模式**和**并行分片**的核心。

**功能点**:
1.  **生命周期管理**: `docker run` -> 等待结束 -> `docker rm`
2.  **并行分片**: 动态计算分片参数，启动 N 个容器
3.  **资源限制**: 控制 CPU/内存配额
4.  **日志收集**: 捕获容器 stdout/stderr 并存储

**分片配置示例**:
```yaml
job: sync_kline
type: docker_parallel
image: gsd-worker:latest
parallelism: 4
command_template: "python -m jobs.sync --shard={shard_index} --total={total_shards}"
error_handling:
  max_retries: 3
  retry_delay: 60s
  timeout: 30m
  on_failure: notify  # skip / block / notify
resource_limits:
  memory: "2G"
  cpus: "1.0"
```

### 2.3 DAG 编排引擎 (Workflow Engine)

管理任务间的依赖关系。

**支持逻辑**:
-   **顺序执行**: A -> B -> C
-   **扇出/扇入 (Fan-out/Fan-in)**: A -> [B1, B2, B3] -> C
-   **条件执行**: 如果 A 成功则 B，否则 C
-   **失败策略**: 重试 (Retry)、跳过 (Skip)、阻断 (Block)

**状态流转**:
`PENDING` -> `RUNNING` -> `SUCCESS` / `FAILED` -> `RETRYING`

### 2.4 告警与通知 (Notifier)

分级告警机制。

| 级别 | 通道 | 场景 |
|:-----|:-----|:-----|
| **INFO** | 每日报告 | "今日数据同步完成，耗时 5m" |
| **WARNING** | 企微群 | "数据缺失 30 只，已自动修复" |
| **CRITICAL** | 电话/短信/钉钉 | "全市场数据缺失，修复失败！" |

---

## 3. 任务定义 (YAML)

使用 YAML 定义工作流，易于版本控制。

```yaml
# workflows/daily_pipeline.yaml
name: 每日数据管道
trigger:
  type: trading_calendar
  time: "18:00"

stages:
  - name: Wait Upstream
    task: check_upstream_ready
    timeout: 30m

  - name: Parallel Sync
    task: sync_kline_parallel
    type: docker
    image: gsd-worker:latest
    parallelism: 4
    depends_on: [Wait Upstream]

  - name: Quality Check
    task: quality_check
    type: docker
    image: gsd-worker:latest
    command: "python -m jobs.quality"
    depends_on: [Parallel Sync]

  - name: Auto Repair
    task: auto_repair
    type: docker
    image: gsd-worker:latest
    command: "python -m jobs.repair"
    condition: "steps.Quality_Check.output.missing_count > 0"
    depends_on: [Quality Check]

  - name: Notify
    task: send_report
    always_run: true
```

---

## 4. 关键技术点实现

### 4.1 交易日历集成
直接集成 `libs/gsd-shared` 中的日历逻辑，或者调用 `gsd-api` 的日历接口（为了减少依赖，建议集成代码）。

### 4.2 Docker 控制
使用 `docker-py` (Python Docker SDK)。
需要挂载 `/var/run/docker.sock` 进 orchestrator 容器。

### 4.3 状态持久化
使用 SQLite (轻量级) 或 MySQL 存储任务执行记录、状态快照。
Redis 用于实时锁和临时状态。

**存储策略**:
- 任务执行记录保留 90 天
- 失败任务保留完整日志
- 定期清理 (每周)

### 4.4 监控指标

暴露 Prometheus 指标用于监控:

```python
# 核心指标
task_execution_duration_seconds{workflow, task, status}
task_execution_total{workflow, task, status="success|failed"}
parallel_containers_running{workflow}
workflow_queue_length
container_cleanup_failures_total
```

**告警规则**:
- 任务连续失败 3 次 → WARNING
- 容器清理失败 → CRITICAL
- 队列积压 > 10 → WARNING

### 4.5 YAML 表达式解析

使用 **Jinja2** 作为条件表达式引擎:

```yaml
condition: "{{ steps.Quality_Check.output.missing_count > 0 }}"
```

**支持的表达式**:
- 变量引用: `{{ steps.task_name.output.field }}`
- 逻辑运算: `and`, `or`, `not`
- 比较运算: `>`, `<`, `==`, `!=`

### 4.6 安全加固

**Docker 容器安全**:
```yaml
security:
  read_only: true  # 只读文件系统
  cap_drop: ["ALL"]  # 移除所有 Capabilities
  no_new_privileges: true
  network_mode: "custom_network"  # 隔离网络
```

**Socket 挂载风险缓解**:
- orchestrator 以受限用户运行
- 仅挂载必要的 `/var/run/docker.sock`
- 定期审计容器启动日志

---

## 5. 异常情况处理

### 5.1 孤儿容器清理

**问题**: orchestrator 崩溃后，可能留下运行中的容器。

**解决方案**:
```python
async def cleanup_orphan_containers():
    """启动时清理上次遗留的容器"""
    containers = docker_client.containers.list(
        filters={"label": "managed_by=task-orchestrator"}
    )
    for c in containers:
        if is_stale(c):  # 超过 2 小时
            c.stop(timeout=30)
            c.remove()
```

### 5.2 网络配置

所有 worker 容器加入同一 Docker Network:

```yaml
networks:
  stock_data_network:
    external: true

services:
  gsd-worker:
    networks:
      - stock_data_network
```

**访问路径**:
- gsd-worker → ClickHouse: `clickhouse:8123`
- gsd-worker → MySQL (云端): 通过 host 网络

### 5.3 部分分片失败

如果 4 个分片中 1 个失败:

| 策略 | 行为 |
|:-----|:-----|
| **Continue** | 其他分片继续，记录失败 |
| **Retry** | 仅重试失败分片 |
| **Abort** | 停止所有分片，回滚 |

推荐: **Retry** 模式，最多 3 次。

---

## 6. 开发计划

1.  **基础框架**: 搭建 FastAPI + APScheduler 骨架
2.  **Trigger 实现**: 移植 CalendarService，实现 TradingDayTrigger
3.  **Executor 实现**: 封装 Docker SDK，实现 ParallelContainerExecutor
4.  **DAG 引擎**: 实现简单的任务依赖解析和执行器调度 (使用 Jinja2)
5.  **监控集成**: Prometheus metrics + 孤儿容器清理
6.  **API 开发**: 暴露 `/workflows`, `/jobs` 管理接口

---

