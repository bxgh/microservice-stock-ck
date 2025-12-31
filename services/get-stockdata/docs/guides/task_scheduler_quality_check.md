# 数据质量检查定时任务配置

本文档提供 task-scheduler 定时任务的配置方法。

## 任务配置

### 1. 每日数据质量检查

```json
{
  "name": "Daily Data Quality Check",
  "description": "每日数据质量检查（时效性、完整性、重复数据）",
  "task_type": "http",
  "schedule": {
    "type": "cron",
    "cron_expression": "0 20 * * *"
  },
  "config": {
    "url": "http://172.17.0.1:8083/api/v1/quality/run",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "check_type": "daily"
    },
    "timeout": 300
  },
  "enabled": true,
  "retry_policy": {
    "max_retries": 2,
    "retry_interval": 60
  }
}
```

**说明**:
- **执行时间**: 每天 20:00 (交易日结束后)
- **检查内容**: 时效性、日完整性、重复数据
- **超时时间**: 300 秒

### 2. 每周数据质量检查

```json
{
  "name": "Weekly Data Quality Check",
  "description": "每周数据质量检查（含趋势分析）",
  "task_type": "http",
  "schedule": {
    "type": "cron",
    "cron_expression": "0 21 * * 0"
  },
  "config": {
    "url": "http://172.17.0.1:8083/api/v1/quality/run",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "check_type": "weekly"
    },
    "timeout": 600
  },
  "enabled": true,
  "retry_policy": {
    "max_retries": 2,
    "retry_interval": 60
  }
}
```

**说明**:
- **执行时间**: 每周日 21:00
- **检查内容**: 日检查 + 趋势稳定性分析
- **超时时间**: 600 秒

## 创建任务的方法

### 方法 1: 通过 API 创建

```bash
# 创建每日检查任务
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Data Quality Check",
    "description": "每日数据质量检查",
    "task_type": "http",
    "schedule": {
      "type": "cron",
      "cron_expression": "0 20 * * *"
    },
    "config": {
      "url": "http://172.17.0.1:8083/api/v1/quality/run",
      "method": "POST",
      "headers": {"Content-Type": "application/json"},
      "body": {"check_type": "daily"},
      "timeout": 300
    },
    "enabled": true
  }'
```

### 方法 2: 通过 Web UI 创建

1. 访问 http://localhost:8080/docs
2. 找到 `POST /api/v1/tasks` 接口
3. 点击 "Try it out"
4. 粘贴上述 JSON 配置
5. 点击 "Execute"

### 方法 3: 直接插入数据库

```sql
-- 插入到 task-scheduler 的 MySQL 数据库
INSERT INTO tasks (name, description, task_type, schedule_type, cron_expression, config, enabled)
VALUES (
  'Daily Data Quality Check',
  '每日数据质量检查',
  'http',
  'cron',
  '0 20 * * *',
  '{"url": "http://172.17.0.1:8083/api/v1/quality/run", "method": "POST", "body": {"check_type": "daily"}}',
  1
);
```

## 验证任务

### 查看任务列表

```bash
curl http://localhost:8080/api/v1/tasks
```

### 查看任务执行历史

```bash
curl http://localhost:8080/api/v1/tasks/{task_id}/executions
```

### 手动触发任务

```bash
curl -X POST http://localhost:8080/api/v1/tasks/{task_id}/execute
```

## 监控告警（可选）

如果需要在质量检查发现问题时发送告警，可以配置 webhook 任务：

```json
{
  "name": "Quality Alert Webhook",
  "task_type": "webhook",
  "trigger": "on_quality_check_failed",
  "config": {
    "url": "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN",
    "method": "POST",
    "body": {
      "msgtype": "markdown",
      "markdown": {
        "title": "数据质量告警",
        "text": "{{alert_message}}"
      }
    }
  }
}
```

## Cron 表达式参考

| 表达式 | 说明 |
|:------|:----|
| `0 20 * * *` | 每天 20:00 |
| `0 21 * * 0` | 每周日 21:00 |
| `0 */6 * * *` | 每 6 小时 |
| `0 0 1 * *` | 每月 1 日 00:00 |

## 注意事项

1. **网络地址**: `172.17.0.1` 是 Docker 宿主机地址，确保 task-scheduler 容器可以访问
2. **端口**: `8083` 是 get-stockdata 服务的端口
3. **超时**: 根据实际检查耗时调整 timeout 值
4. **重试**: 建议配置重试策略，避免偶发网络问题导致任务失败
