# Data Models

## Task (任务模型)

**Purpose:** 核心任务定义模型，包含调度策略和执行配置

**Key Attributes:**
- id: UUID - 任务唯一标识符
- name: string - 任务名称
- description: string - 任务描述
- task_type: TaskType - 任务类型 (HTTP/SHELL/PLUGIN)
- schedule_config: ScheduleConfig - 调度配置
- execution_config: ExecutionConfig - 执行配置
- status: TaskStatus - 任务状态
- created_at: datetime - 创建时间
- updated_at: datetime - 更新时间

### TypeScript Interface
```typescript
export enum TaskType {
  HTTP = 'http',
  SHELL = 'shell',
  PLUGIN = 'plugin'
}

export enum TaskStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  PAUSED = 'paused',
  DELETED = 'deleted'
}

export interface ScheduleConfig {
  cron_expression?: string;
  interval_seconds?: number;
  event_trigger?: string;
  timezone: string;
  retry_config: RetryConfig;
}

export interface ExecutionConfig {
  timeout_seconds: number;
  max_retries: number;
  retry_delay_seconds: number;
  environment_vars?: Record<string, string>;
}

export interface Task {
  id: string;
  name: string;
  description: string;
  task_type: TaskType;
  schedule_config: ScheduleConfig;
  execution_config: ExecutionConfig;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
}
```

## TaskExecution (任务执行记录)

**Purpose:** 记录每次任务执行的详细信息和结果

**Key Attributes:**
- id: UUID - 执行记录唯一标识符
- task_id: UUID - 关联的任务ID
- execution_id: string - 本次执行标识符
- status: ExecutionStatus - 执行状态
- started_at: datetime - 开始时间
- finished_at: datetime - 结束时间
- duration_ms: number - 执行时长(毫秒)
- result: ExecutionResult - 执行结果
- error_message?: string - 错误信息
- logs: string[] - 执行日志

### TypeScript Interface
```typescript
export enum ExecutionStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  SUCCESS = 'success',
  FAILED = 'failed',
  TIMEOUT = 'timeout',
  CANCELLED = 'cancelled'
}

export interface ExecutionResult {
  return_code: number;
  output_data?: any;
  metrics?: Record<string, number>;
  artifacts?: string[];
}

export interface TaskExecution {
  id: string;
  task_id: string;
  execution_id: string;
  status: ExecutionStatus;
  started_at: string;
  finished_at?: string;
  duration_ms?: number;
  result?: ExecutionResult;
  error_message?: string;
  logs: string[];
}
```

## DataSource (数据源模型)

**Purpose:** DataCollector 服务使用的数据源配置

**Key Attributes:**
- id: UUID - 数据源唯一标识符
- name: string - 数据源名称
- source_type: DataSourceType - 数据源类型
- connection_config: ConnectionConfig - 连接配置
- collection_config: CollectionConfig - 采集配置
- status: DataSourceStatus - 数据源状态
- health_check_url?: string - 健康检查地址

### TypeScript Interface
```typescript
export enum DataSourceType {
  DATABASE = 'database',
  API = 'api',
  FILE = 'file',
  MESSAGE_QUEUE = 'message_queue'
}

export interface ConnectionConfig {
  host: string;
  port: number;
  username?: string;
  password?: string;
  database?: string;
  ssl_enabled: boolean;
  connection_params?: Record<string, any>;
}

export interface CollectionConfig {
  collection_interval_seconds: number;
  batch_size: number;
  timeout_seconds: number;
  retry_config: RetryConfig;
}

export interface DataSource {
  id: string;
  name: string;
  source_type: DataSourceType;
  connection_config: ConnectionConfig;
  collection_config: CollectionConfig;
  status: DataSourceStatus;
  health_check_url?: string;
  created_at: string;
  updated_at: string;
}
```
