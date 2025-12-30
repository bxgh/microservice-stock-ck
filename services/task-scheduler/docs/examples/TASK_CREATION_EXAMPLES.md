# TaskScheduler 任务创建示例

本文档提供了在 TaskScheduler 中创建调度任务的实际示例。

## ✅ 已创建的示例任务

系统当前运行了以下三个示例任务：

### 1. get_stockdata_health_check
**类型**: HTTP 健康检查  
**调度**: 每分钟执行 (`* * * * *`)  
**目标**: http://get-stockdata:8083/api/v1/health  
**用途**: 监控 get-stockdata 服务健康状态

```bash
curl -X POST http://localhost:8081/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_stockdata_health_check",
    "task_type": "http",
    "description": "每分钟检查 get-stockdata 服务健康状态",
    "enabled": true,
    "cron_expression": "* * * * *",
    "timeout": 10,
    "max_retries": 2,
    "config": {
      "url": "http://get-stockdata:8083/api/v1/health",
      "method": "GET"
    },
    "tags": ["health", "monitoring"]
  }'
```

### 2. quant_strategy_heartbeat
**类型**: HTTP 心跳检查  
**调度**: 每30秒执行 (interval_seconds: 30)  
**目标**: http://quant-strategy:8084/api/v1/health  
**用途**: 监控量化策略服务心跳

```bash
curl -X POST http://localhost:8081/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "quant_strategy_heartbeat",
    "task_type": "http",
    "description": "每30秒检查量化策略服务心跳",
    "enabled": true,
    "interval_seconds": 30,
    "timeout": 5,
    "max_retries": 1,
    "config": {
      "url": "http://quant-strategy:8084/api/v1/health",
      "method": "GET"
    },
    "tags": ["heartbeat", "quant-strategy"]
  }'
```

### 3. daily_system_stats
**类型**: HTTP 统计收集  
**调度**: 每天上午9点 (`0 9 * * *`)  
**目标**: http://localhost:8081/api/v1/stats  
**用途**: 定时收集系统统计信息

```bash
curl -X POST http://localhost:8081/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily_system_stats",
    "task_type": "http",
    "description": "每天上午9点收集系统统计信息",
    "enabled": true,
    "cron_expression": "0 9 * * *",
    "timeout": 60,
    "max_retries": 3,
    "config": {
      "url": "http://localhost:8081/api/v1/stats",
      "method": "GET"
    },
    "tags": ["stats", "daily"]
  }'
```

## 📋 更多实用示例

### Shell 任务示例

```bash
# 每小时清理临时文件
curl -X POST http://localhost:8081/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cleanup_temp_files",
    "task_type": "shell",
    "description": "每小时清理临时文件",
    "enabled": true,
    "cron_expression": "0 * * * *",
    "timeout": 120,
    "config": {
      "command": "find /tmp -type f -mtime +1 -delete",
      "cwd": "/tmp"
    },
    "tags": ["cleanup", "maintenance"]
  }'
```

### POST 请求示例

```bash
# 每5分钟触发数据同步
curl -X POST http://localhost:8081/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "stock_data_sync",
    "task_type": "http",
    "description": "每5分钟同步股票数据",
    "enabled": true,
    "cron_expression": "*/5 * * * *",
    "timeout": 300,
    "max_retries": 3,
    "config": {
      "url": "http://data-collector:8089/api/v1/sync",
      "method": "POST",
      "headers": "{\"Content-Type\": \"application/json\"}",
      "body": "{\"source\": \"tushare\", \"symbols\": [\"000001.SZ\", \"600000.SH\"]}"
    },
    "tags": ["stock", "sync", "data"]
  }'
```

### 工作日定时任务

```bash
# 周一到周五上午9:30开盘前准备
curl -X POST http://localhost:8081/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "market_open_preparation",
    "task_type": "http",
    "description": "每个交易日开盘前数据预加载",
    "enabled": true,
    "cron_expression": "25 9 * * 1-5",
    "timeout": 180,
    "config": {
      "url": "http://data-collector:8089/api/v1/preload",
      "method": "POST"
    },
    "tags": ["market", "trading-hours"]
  }'
```

## 🔍 查看和管理任务

```bash
# 查看所有任务
curl http://localhost:8081/api/v1/tasks

# 查看特定任务详情
curl http://localhost:8081/api/v1/tasks/{task_id}

# 手动触发任务执行
curl -X POST http://localhost:8081/api/v1/tasks/{task_id}/trigger

# 暂停任务
curl -X POST http://localhost:8081/api/v1/tasks/{task_id}/pause

# 恢复任务
curl -X POST http://localhost:8081/api/v1/tasks/{task_id}/resume

# 删除任务
curl -X DELETE http://localhost:8081/api/v1/tasks/{task_id}
```

## 📊 监控任务执行

```bash
# 查看服务统计
curl http://localhost:8081/api/v1/stats

# 查看任务统计 (30天)
curl http://localhost:8081/api/v1/tasks/{task_id}/statistics?days=30
```

## 💡 最佳实践

1. **合理设置超时时间**: 根据任务复杂度设置合理的 `timeout`
2. **使用标签分类**: 通过 `tags` 便于任务分类和筛选
3. **设置重试策略**: 为网络请求设置 `max_retries` 提高稳定性
4. **使用描述性名称**: `name` 和 `description` 应清晰描述任务用途
5. **测试 cron 表达式**: 使用在线工具验证 cron 表达式正确性

## 🌐 可视化管理

访问 Swagger UI 进行可视化操作:
- **URL**: http://localhost:8081/docs
- **功能**: 查看 API 文档、测试接口、查看响应示例

---

**创建时间**: 2025-12-24  
**服务版本**: TaskScheduler v2.0.0
