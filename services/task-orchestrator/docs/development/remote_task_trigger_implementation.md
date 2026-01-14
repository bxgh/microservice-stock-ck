# 远程任务触发与参数化补采系统实现文档

## 1. 概述
为了实现移动端小程序对内网数据采集任务的控制，我们构建了一套“云端触发 -> 内网执行”的远程命令系统。该系统利用现有的 SSH 反向隧道基础设施，实现了安全的穿透控制，并支持带参数的任务执行（如按日期补采数据）。

## 2. 核心架构

### 2.1 数据流图
```mermaid
graph LR
    User[小程序/管理员] -->|1. 插入命令| CloudDB[(云端 MySQL)]
    CloudDB -->|task_commands 表| ReverseTunnel[SSH 反向隧道]
    ReverseTunnel -->|端口映射 36301| LocalPoller[内网 CommandPoller]
    LocalPoller -->|2. 轮询 & 解析| TaskOrchestrator[任务编排器]
    TaskOrchestrator -->|3. 启动容器| DockerWorker[GSD Worker 容器]
    DockerWorker -->|4. 执行同步| DataSources[外部数据源]
    DockerWorker -->|5. 写入数据| ClickHouse[(内网 ClickHouse)]
    LocalPoller -->|6. 回写状态| CloudDB
```

### 2.2 关键组件
1.  **AlwaysUp Cloud MySQL (`task_commands`)**: 作为命令队列，存储待执行的任务指令及参数。
2.  **CommandPoller (Local)**: 运行在 `task-orchestrator` 中的异步服务，负责周期性轮询云端数据库，拉取 `PENDING` 状态的命令。
3.  **DockerExecutor**: 增强版的执行器，支持动态注入环境变量和命令行参数（如 `--date 20260113`）。
4.  **GSD Worker (`sync_service`)**: 业务执行单元，新增了 `sync_by_date` 方法支持按日精准同步。

## 3. 数据库设计

### 云端表结构 (`alwaysup.task_commands`)
用于存储命令队列。

```sql
CREATE TABLE IF NOT EXISTS `task_commands` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL COMMENT '对应 tasks.yml 中的任务ID',
    `params` JSON COMMENT '动态参数，如 {"date": "20260113"}',
    `status` ENUM('PENDING', 'RUNNING', 'DONE', 'FAILED') DEFAULT 'PENDING',
    `result` TEXT COMMENT '执行结果或错误日志',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 4. 功能实现细节

### 4.1 CommandPoller (轮询器)
*   **位置**: `services/task-orchestrator/src/core/command_poller.py`
*   **逻辑**:
    1.  每 15 秒通过本地隧道 (`127.0.0.1:36301`) 连接云端 MySQL。
    2.  查询 `status='PENDING'` 的记录。
    3.  锁定记录（`status='RUNNING'`）。
    4.  查找本地 `tasks.yml` 中对应的任务定义。
    5.  调用 `DockerExecutor` 执行任务，并阻塞等待完成。
    6.  更新执行结果 (`DONE`/`FAILED`) 和日志到云端。

### 4.2 参数化执行支持
*   **在 `tasks.yml` 中新增专用任务**:
    *   `repair_kline`: 用于 K 线按日补采。
    *   `repair_tick`: 用于分笔数据按日补采。
    *   这些任务默认 `enabled: false`，不参与定时调度，专供 Poller 触发。
*   **参数注入**:
    *   云端 JSON 参数 `{"date": "20260113"}` 会被自动转换为命令行参数 `--date 20260113` 传递给容器。

### 4.3 业务层支持 (GSD Worker)
*   **K线同步**: `KLineSyncService` 新增 `sync_by_date` 方法。
    *   逻辑: 从 Redis 获取股票列表 -> 根据日期查询 MySQL -> 写入 ClickHouse -> 校验一致性。
*   **Redis 兼容性**: 修复了 `sync_service.py`，根据 `REDIS_CLUSTER` 环境变量自动切换 `Redis` (单机) 或 `RedisCluster` (集群) 客户端，确保在不同环境下的稳定性。

## 5. 使用指南

### 5.1 手动触发补采 (SQL 示例)
管理员可直接操作云端数据库触发任务：

```sql
-- 触发 2026-01-13 的 K 线补采
INSERT INTO task_commands (task_id, params) 
VALUES ('repair_kline', '{"date": "20260113"}');
```

### 5.2 监控与排查
*   **查看进度**:
    ```sql
    SELECT * FROM task_commands ORDER BY id DESC LIMIT 5;
    ```
*   **查看日志**:
    *   成功: `result` 字段会包含 "Success (Ad-hoc). Logs tail..."
    *   失败: `result` 字段会包含错误堆栈。

## 6. 验证记录
*   **测试脚本**: `services/task-orchestrator/tests/verify_command_execution.py`
*   **测试结果**: 全流程验证通过。不仅验证了命令下发，还验证了容器内的 Redis 连接和 ClickHouse 写入能力。

## 7. 后续计划
*   **接口封装**: 在云端 FastAPI 封装 `/api/v1/commands` 接口，供小程序调用。
*   **告警集成**: 任务执行失败时发送 Feishu/DingTalk 消息。
