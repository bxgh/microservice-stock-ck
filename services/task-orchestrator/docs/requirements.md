# Task Orchestrator 功能需求文档

**版本**: 1.0  
**日期**: 2026-01-02  
**状态**: 需求定义

---

## 1. 核心目标

**统一任务调度中心**：集中管理所有定时任务，实现"单一调度源"原则。

---

## 2. 核心功能清单

### 2.1 任务调度 (P0 - 必需)

#### F1.1 交易日历感知调度

**需求**:
- 支持 `trading_cron` 类型，自动过滤非交易日
- 基于 `chinesecalendar` 库
- 支持手动覆盖 (如补班日)

**示例**:
```yaml
schedule:
  type: trading_cron
  expression: "5 15 * * 1-5"  # 仅交易日 15:05
```

**验证标准**:
- ✅ 非交易日 (周末、节假日) 不触发
- ✅ 交易日正常触发

---

#### F1.2 标准Cron调度

**需求**:
- 支持标准 Cron 表达式
- 时区: Asia/Shanghai

**示例**:
```yaml
schedule:
  type: cron
  expression: "0 3 * * *"  # 每日 03:00
```

---

#### F1.3 一次性任务

**需求**:
- 支持指定时间执行一次
- 执行后自动移除

**示例**:
```yaml
schedule:
  type: date
  run_date: "2026-01-10 18:00:00"
```

---

### 2.2 任务类型 (P0 - 必需)

#### F2.1 Docker容器任务

**需求**:
- 通过 Docker SDK 启动临时容器
- 支持环境变量注入
- 支持 volume 挂载
- 自动 `--rm` (执行后删除)

**配置**:
```yaml
type: docker
target:
  image: gsd-worker:latest
  command: ["jobs.sync_kline", "--shard", "0", "--total", "4"]
  environment:
    MYSQL_HOST: 127.0.0.1
  volumes:
    - ./libs/gsd-shared:/app/libs/gsd-shared:ro
  network_mode: host
```

---

#### F2.2 HTTP回调任务

**需求**:
- 调用其他服务的 HTTP API
- 支持 Nacos 服务发现 (可选)
- 支持重试和超时

**配置**:
```yaml
type: http
target:
  service: gsd-api              # Nacos 服务名
  endpoint: /api/v1/warmup      # 或直接 URL
  method: POST
  timeout_seconds: 60
  headers:
    Authorization: "Bearer xxx"
```

---

#### F2.3 Workflow 工作流

**需求**:
- 支持 DAG (有向无环图) 任务依赖
- 并行执行支持
- 失败处理策略

**配置**:
```yaml
type: workflow
workflow:
  - id: step1
    parallel: true
    tasks:
      - {id: shard-0, command: ["jobs.sync_kline", "--shard", "0"]}
      - {id: shard-1, command: ["jobs.sync_kline", "--shard", "1"]}
  - id: step2
    command: ["jobs.quality_check"]
    depends_on: [step1]
```

---

### 2.3 错误处理 (P0 - 必需)

#### F3.1 重试机制

**需求**:
- 可配置重试次数
- 指数退避策略
- 可配置重试条件 (exit code, timeout)

**配置**:
```yaml
retry:
  max_attempts: 3
  backoff_seconds: 60      # 初始退避时间
  backoff_multiplier: 2    # 指数倍数 (60s, 120s, 240s)
  retry_on:
    - exit_code: [1, 2]    # 仅重试特定退出码
```

---

#### F3.2 失败告警

**需求**:
- 任务失败时发送告警
- 支持多种告警渠道

**配置**:
```yaml
notifications:
  on_failure:
    - type: webhook
      url: "https://qyapi.weixin.qq.com/xxx"
    - type: email
      to: "admin@example.com"
```

---

#### F3.3 熔断机制

**需求**:
- 连续失败 N 次后暂停任务
- 手动或自动恢复

**配置**:
```yaml
circuit_breaker:
  failure_threshold: 5       # 连续失败 5 次
  recovery_timeout: 3600     # 1小时后自动恢复
```

---

### 2.4 YAML 配置管理 (P1 - 重要)

#### F4.1 配置文件加载

**需求**:
- 自动加载 `config/tasks.yml`
- 支持环境变量替换

**示例**:
```yaml
environment:
  MYSQL_HOST: ${MYSQL_HOST:-127.0.0.1}  # 环境变量 + 默认值
```

---

#### F4.2 热重载

**需求**:
- 修改 YAML 后无需重启
- 通过 API 触发重载

**API**:
```bash
POST /api/v1/reload
```

---

#### F4.3 配置验证

**需求**:
- 启动时验证 YAML 语法
- 验证任务 ID 唯一性
- 验证依赖关系无环

---

### 2.5 监控与可观测性 (P1 - 重要)

#### F5.1 任务执行历史

**需求**:
- 记录每次执行的详细信息
- 持久化到数据库 (MySQL)

**字段**:
```sql
CREATE TABLE task_execution_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(100),
    task_name VARCHAR(200),
    status ENUM('SUCCESS', 'FAILED', 'TIMEOUT'),
    start_time DATETIME,
    end_time DATETIME,
    duration_seconds INT,
    exit_code INT,
    error_message TEXT,
    created_at DATETIME DEFAULT NOW()
);
```

---

#### F5.2 Prometheus 指标

**需求**:
- 任务执行总数
- 任务执行耗时分布
- 任务成功/失败率

**指标**:
```python
task_executions_total{task_id, status}
task_execution_duration_seconds{task_id}
task_failures_total{task_id}
```

---

#### F5.3 实时状态查询

**API**:
```bash
GET /api/v1/tasks              # 所有任务列表
GET /api/v1/tasks/{id}         # 任务详情
GET /api/v1/tasks/{id}/history # 执行历史
GET /api/v1/tasks/{id}/status  # 当前状态
```

---

### 2.6 手动控制 (P2 - 可选)

#### F6.1 手动触发

**需求**:
- 手动触发任意任务
- 支持传入自定义参数

**API**:
```bash
POST /api/v1/tasks/{id}/trigger
{
  "params": {
    "shard": 0,
    "total": 1
  }
}
```

---

#### F6.2 任务暂停/恢复

**API**:
```bash
POST /api/v1/tasks/{id}/pause   # 暂停调度
POST /api/v1/tasks/{id}/resume  # 恢复调度
```

---

#### F6.3 终止运行中的任务

**需求**:
- 终止 Docker 容器
- 记录终止原因

**API**:
```bash
POST /api/v1/tasks/{id}/stop
```

---

## 3. 预定义任务清单

### 3.1 数据同步任务

| 任务ID | 名称 | 频率 | 优先级 |
|:-------|:-----|:-----|:-------|
| `daily_kline_sync` | K线每日同步 | 15:05 交易日 | P0 |
| `weekly_financial_sync` | 财务数据更新 | 周六 06:00 | P1 |
| `monthly_valuation_sync` | 估值数据更新 | 每月1号 06:00 | P2 |

### 3.2 数据质量任务

| 任务ID | 名称 | 频率 | 优先级 |
|:-------|:-----|:-----|:-------|
| `daily_quality_check` | 每日质量检查 | 15:20 交易日 | P0 |
| `daily_data_repair` | 数据自动修复 | 15:30 交易日 | P0 |
| `monthly_audit` | 月度数据审计 | 每月5号 03:00 | P2 |

### 3.3 策略任务

| 任务ID | 名称 | 频率 | 优先级 |
|:-------|:-----|:-----|:-------|
| `daily_strategy_scan` | 每日策略扫描 | 18:30 交易日 | P1 |
| `weekly_backtest` | 周末策略回测 | 周日 08:00 | P2 |

### 3.4 系统维护任务

| 任务ID | 名称 | 频率 | 优先级 |
|:-------|:-----|:-----|:-------|
| `daily_db_backup` | 数据库备份 | 每日 03:00 | P0 |
| `daily_cache_warmup` | 缓存预热 | 09:00 交易日 | P1 |
| `weekly_log_cleanup` | 日志清理 | 周日 02:00 | P2 |

---

## 4. 实施优先级

### 阶段 1: 核心功能 (P0)

**目标**: 完成基础调度能力

- ✅ 交易日历感知调度 (已实现)
- ✅ Docker 任务执行 (已实现)
- ✅ DAG 工作流 (已实现)
- ⚠️ YAML 配置加载 (待实现)
- ⚠️ 任务执行日志 (待实现)
- ⚠️ 重试机制 (待实现)

**交付物**:
- tasks.yml 配置文件
- YAML 加载逻辑
- 任务执行日志表

---

### 阶段 2: 可观测性 (P1)

**目标**: 增强监控和告警

- ⚠️ Prometheus 指标
- ⚠️ 失败告警
- ⚠️ 执行历史 API
- ⚠️ 实时状态查询

**交付物**:
- Prometheus metrics endpoint
- 告警集成
- 管理 API

---

### 阶段 3: 高级功能 (P2)

**目标**: 用户体验优化

- ⚠️ 手动触发 API
- ⚠️ 任务暂停/恢复
- ⚠️ 配置热重载
- ⚠️ Web UI (可选)

---

## 5. API 规范

### 5.1 任务管理

```bash
# 列出所有任务
GET /api/v1/tasks
Response: [
  {
    "id": "daily_kline_sync",
    "name": "K线每日同步",
    "enabled": true,
    "next_run_time": "2026-01-03T15:05:00+08:00",
    "last_run_status": "SUCCESS"
  }
]

# 获取任务详情
GET /api/v1/tasks/{id}
Response: {
  "id": "daily_kline_sync",
  "schedule": {...},
  "retry": {...},
  "statistics": {
    "total_runs": 120,
    "success_rate": 0.983
  }
}

# 手动触发
POST /api/v1/tasks/{id}/trigger

# 暂停/恢复
POST /api/v1/tasks/{id}/pause
POST /api/v1/tasks/{id}/resume

# 重载配置
POST /api/v1/reload
```

### 5.2 执行历史

```bash
# 获取执行历史
GET /api/v1/tasks/{id}/history?limit=20
Response: [
  {
    "id": 12345,
    "task_id": "daily_kline_sync",
    "status": "SUCCESS",
    "start_time": "2026-01-02T15:05:00+08:00",
    "duration_seconds": 180,
    "error_message": null
  }
]
```

---

## 6. 配置文件规范

### 完整示例: tasks.yml

```yaml
version: "1.0"
timezone: "Asia/Shanghai"

# 全局配置
global:
  docker:
    network_mode: host
    default_volumes:
      - ./libs/gsd-shared:/app/libs/gsd-shared:ro
  notifications:
    on_failure:
      - type: webhook
        url: "${ALERT_WEBHOOK_URL}"

# 任务列表
tasks:
  # K线同步 (P0)
  - id: daily_kline_sync
    name: K线每日同步
    type: workflow
    enabled: true
    schedule:
      type: trading_cron
      expression: "5 15 * * 1-5"
    workflow:
      - id: sync-shards
        parallel: true
        tasks:
          - {id: sync-0, command: ["jobs.sync_kline", "--shard", "0", "--total", "4"]}
          - {id: sync-1, command: ["jobs.sync_kline", "--shard", "1", "--total", "4"]}
          - {id: sync-2, command: ["jobs.sync_kline", "--shard", "2", "--total", "4"]}
          - {id: sync-3, command: ["jobs.sync_kline", "--shard", "3", "--total", "4"]}
      - id: quality-check
        command: ["jobs.quality_check", "--deep"]
        depends_on: [sync-shards]
      - id: data-repair
        command: ["jobs.data_repair"]
        depends_on: [quality-check]
    retry:
      max_attempts: 2
      backoff_seconds: 600
  
  # 策略扫描 (P1)
  - id: daily_strategy_scan
    name: 每日策略扫描
    type: docker
    enabled: true
    schedule:
      type: trading_cron
      expression: "30 18 * * 1-5"
    target:
      image: quant-strategy:latest
      command: ["jobs.daily_scan"]
    dependencies: [daily_kline_sync]
    retry:
      max_attempts: 2
  
  # 数据库备份 (P0)
  - id: daily_db_backup
    name: 数据库备份
    type: docker
    enabled: true
    schedule:
      type: cron
      expression: "0 3 * * *"
    target:
      image: gsd-worker:latest
      command: ["jobs.db_backup"]
    retry:
      max_attempts: 3
    circuit_breaker:
      failure_threshold: 3
```

---

## 7. 验收标准

### 阶段 1 验收

- [ ] 可从 YAML 加载任务配置
- [ ] 交易日历过滤正确 (非交易日不运行)
- [ ] Docker 任务可正常执行
- [ ] 任务执行日志写入 MySQL
- [ ] 失败任务可自动重试
- [ ] 手动触发 API 可用

### 阶段 2 验收

- [ ] Prometheus metrics 可被抓取
- [ ] 任务失败时有告警通知
- [ ] 执行历史 API 可查询
- [ ] 实时状态准确

### 阶段 3 验收

- [ ] 暂停/恢复功能正常
- [ ] 配置热重载无需重启
- [ ] 所有 API 响应 < 200ms

---

**维护**: 随功能迭代同步更新  
**版本**: 1.0 (2026-01-02)
