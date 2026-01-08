# Database Schema

## MySQL 5.7 Schema (元数据存储)

```sql
-- 任务表
CREATE TABLE tasks (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    task_type ENUM('http', 'shell', 'plugin') NOT NULL,
    status ENUM('active', 'inactive', 'paused', 'deleted') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_tasks_status (status),
    INDEX idx_tasks_type (task_type),
    INDEX idx_tasks_created (created_at),
    INDEX idx_tasks_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 调度配置表
CREATE TABLE task_schedule_configs (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    task_id VARCHAR(36) NOT NULL,
    cron_expression VARCHAR(100),
    interval_seconds INT,
    event_trigger VARCHAR(255),
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Shanghai',
    max_attempts INT DEFAULT 3,
    delay_seconds INT DEFAULT 60,
    backoff_multiplier DECIMAL(3,1) DEFAULT 2.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    INDEX idx_schedule_task (task_id),
    INDEX idx_schedule_cron (cron_expression)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 任务执行记录表
CREATE TABLE task_executions (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    task_id VARCHAR(36) NOT NULL,
    execution_id VARCHAR(100) NOT NULL,
    status ENUM('pending', 'running', 'success', 'failed', 'timeout', 'cancelled') DEFAULT 'pending',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP NULL,
    duration_ms INT,
    return_code INT,
    output_data JSON,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    INDEX idx_execution_task (task_id),
    INDEX idx_execution_status (status),
    INDEX idx_execution_started (started_at),
    INDEX idx_execution_id (execution_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 数据源表
CREATE TABLE data_sources (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(255) NOT NULL,
    source_type ENUM('database', 'api', 'file', 'message_queue') NOT NULL,
    connection_config JSON NOT NULL,
    collection_config JSON NOT NULL,
    status ENUM('active', 'inactive', 'error') DEFAULT 'active',
    health_check_url VARCHAR(2048),
    last_health_check TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_datasource_type (source_type),
    INDEX idx_datasource_status (status),
    INDEX idx_datasource_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## ClickHouse Schema (实时数据存储)

```sql
-- 任务执行指标表
CREATE TABLE task_execution_metrics (
    timestamp DateTime DEFAULT now(),
    task_id String,
    execution_id String,
    metric_name String,
    metric_value Float64,
    tags Map(String, String)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, task_id, metric_name)
TTL timestamp + INTERVAL 30 DAY;

-- 系统性能指标表
CREATE TABLE system_metrics (
    timestamp DateTime DEFAULT now(),
    service_name String,
    metric_name String,
    metric_value Float64,
    tags Map(String, String)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, service_name, metric_name)
TTL timestamp + INTERVAL 7 DAY;

-- 数据采集记录表
CREATE TABLE data_collection_records (
    timestamp DateTime DEFAULT now(),
    data_source_id String,
    collection_type String,
    records_count UInt64,
    data_size_bytes UInt64,
    collection_duration_ms UInt32,
    status Enum8('success' = 1, 'failed' = 2),
    error_message String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, data_source_id, collection_type)
TTL timestamp + INTERVAL 90 DAY;

> [!NOTE]
> 所有核心股票数据表（K线、分笔、快照等）已从标准 `MergeTree` 系列引擎迁移至 `Replicated` 引擎（如 `ReplicatedReplacingMergeTree`），以支持 Server 41 和 Server 58 之间的双主同步。
> 详细的集群拓扑和引擎规范请参阅 [ClickHouse 双主复制集群](./clickhouse-replicated-cluster.md)。

```

## Redis Data Structures (缓存和消息队列)

```redis
# 消息队列频道
channels:
  - task.created          # 任务创建事件
  - task.updated          # 任务更新事件
  - task.deleted          # 任务删除事件
  - task.scheduled        # 任务调度事件
  - task.execution.start  # 任务执行开始
  - task.execution.success # 任务执行成功
  - task.execution.failed # 任务执行失败
  - data.collected        # 数据采集完成
  - data.processed        # 数据处理完成
  - data.stored          # 数据存储完成
  - system.health.check  # 系统健康检查
  - alert.triggered      # 告警触发

# 缓存键命名规范
cache_keys:
  - task:{task_id}                    # 任务详情缓存
  - task:list:page:{page}:limit:{limit} # 任务列表缓存
  - datasource:{datasource_id}       # 数据源详情缓存
  - system:health:{service_name}     # 服务健康状态缓存
  - metrics:system:{timestamp}       # 系统指标缓存
  - config:{config_key}              # 系统配置缓存

# 分布式锁
locks:
  - task:execution:{task_id}         # 任务执行锁
  - datasource:collection:{datasource_id} # 数据采集锁
  - config:update                    # 配置更新锁
```
