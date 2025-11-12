# 基础使用示例

## 🚀 快速开始

### 1. 创建HTTP任务
```python
from client.taskscheduler_client import TaskSchedulerClient, create_http_task

# 创建客户端
client = TaskSchedulerClient("http://localhost:8080", api_key="your-api-key")

# 定义HTTP任务
task = create_http_task(
    name="API健康检查",
    url="http://example.com/api/health",
    method="GET",
    cron_expression="*/5 * * * *",  # 每5分钟执行
    timeout=30,
    config={
        "expected_status": 200,
        "headers": {"User-Agent": "TaskScheduler/2.0"}
    }
)

# 创建任务
created_task = client.create_task(task)
print(f"任务创建成功: {created_task.task_id}")
```

### 2. 创建Shell任务
```python
from client.taskscheduler_client import create_shell_task

# 定义Shell任务
shell_task = create_shell_task(
    name="数据备份",
    command="pg_dump mydb > backup_$(date +%Y%m%d).sql",
    cron_expression="0 2 * * *",  # 每天凌晨2点
    timeout=300,
    config={
        "working_directory": "/backup",
        "environment": {
            "PGPASSWORD": "your_password"
        }
    }
)

# 创建任务
backup_task = client.create_task(shell_task)
print(f"备份任务创建成功: {backup_task.task_id}")
```

## 📋 任务管理

### 查询任务列表
```python
# 获取所有任务
tasks = client.list_tasks()
print(f"总任务数: {len(tasks)}")

# 按状态过滤
pending_tasks = client.list_tasks(status="pending")
print(f"等待执行的任务: {len(pending_tasks)}")

# 分页查询
page_1 = client.list_tasks(page=1, page_size=10)
page_2 = client.list_tasks(page=2, page_size=10)
```

### 获取任务详情
```python
# 获取任务详情
task_info = client.get_task("task_id_here")
print(f"任务名称: {task_info.definition.name}")
print(f"任务状态: {task_info.status}")
print(f"执行次数: {task_info.execution_count}")
print(f"成功率: {task_info.success_count}/{task_info.execution_count}")
```

### 更新任务配置
```python
from models.task_models import TaskDefinition

# 更新任务配置
updated_definition = TaskDefinition(
    name="更新后的任务名称",
    task_type="http_request",
    cron_expression="*/10 * * * *",  # 改为每10分钟
    timeout=60,
    config={"url": "http://new-api.example.com/health"}
)

updated_task = client.update_task("task_id_here", updated_definition)
print(f"任务更新成功: {updated_task.task_id}")
```

## 🎮 任务控制

### 手动触发任务
```python
# 立即执行任务
success = client.trigger_task("task_id_here")
if success:
    print("任务触发成功")
else:
    print("任务触发失败")
```

### 暂停和恢复任务
```python
# 暂停任务
client.pause_task("task_id_here")
print("任务已暂停")

# 恢复任务
client.resume_task("task_id_here")
print("任务已恢复")

# 启用/禁用任务
client.enable_task("task_id_here")
client.disable_task("task_id_here")
```

### 删除任务
```python
# 删除任务
success = client.delete_task("task_id_here")
if success:
    print("任务删除成功")
else:
    print("任务删除失败")
```

## 📊 监控和统计

### 服务健康检查
```python
# 检查服务健康状态
health = client.get_health()
print(f"服务状态: {health['status']}")
print(f"调度器运行: {health['scheduler_running']}")
print(f"插件数量: {len(health['plugins'])}")
```

### 获取服务统计
```python
# 获取服务统计信息
stats = client.get_stats()
print(f"总任务数: {stats['total_jobs']}")
print(f"活跃任务数: {stats['active_jobs']}")
print(f"可用插件: {', '.join(stats['plugins'])}")
```

### 任务执行统计
```python
# 获取任务统计（最近7天）
stats = client.get_task_statistics("task_id_here", days=7)
print(f"总执行次数: {stats['total_executions']}")
print(f"成功率: {stats['success_rate']:.2f}%")
print(f"平均执行时间: {stats['avg_duration']:.2f}秒")
```

## 🔧 高级用法

### 批量操作
```python
# 批量创建任务
tasks = []
for i in range(5):
    task = create_http_task(
        name=f"批量任务-{i+1}",
        url=f"http://api.example.com/batch/{i+1}",
        cron_expression=f"{i+1} * * * * *"  # 不同分钟执行
    )
    tasks.append(task)

created_tasks = []
for task in tasks:
    created = client.create_task(task)
    created_tasks.append(created)
    print(f"创建任务: {created.task_id}")
```

### 条件过滤
```python
# 获取所有HTTP任务
all_tasks = client.list_tasks()
http_tasks = [t for t in all_tasks if t.definition.task_type == "http_request"]
print(f"HTTP任务数量: {len(http_tasks)}")

# 获取启用的任务
enabled_tasks = [t for t in all_tasks if t.definition.enabled]
print(f"启用的任务数量: {len(enabled_tasks)}")

# 获取失败的任务
failed_tasks = [t for t in all_tasks if t.failure_count > 0]
print(f"有失败记录的任务: {len(failed_tasks)}")
```

### 错误处理
```python
try:
    # 尝试创建任务
    task = create_http_task(name="测试任务", url="invalid-url")
    created_task = client.create_task(task)
    print(f"任务创建成功: {created_task.task_id}")
except Exception as e:
    print(f"任务创建失败: {e}")
```

### 异步操作
```python
import asyncio
from client.taskscheduler_client import AsyncTaskSchedulerClient

async def async_examples():
    async with AsyncTaskSchedulerClient("http://localhost:8080") as client:
        # 异步创建任务
        task = create_http_task(name="异步任务", url="http://example.com")
        created = await client.create_task(task)
        print(f"异步创建任务成功: {created.task_id}")

        # 异步查询任务
        tasks = await client.list_tasks()
        print(f"异步查询到 {len(tasks)} 个任务")

# 运行异步示例
asyncio.run(async_examples())
```

## 🎯 实际应用场景

### 1. 数据处理管道
```python
# 数据抽取任务
extract_task = create_http_task(
    name="数据抽取",
    url="http://data-api.example.com/extract",
    cron_expression="0 */2 * * *",  # 每2小时
    config={"format": "json", "batch_size": 1000}
)

# 数据转换任务
transform_task = create_shell_task(
    name="数据转换",
    command="python3 transform_data.py",
    cron_expression="15 */2 * * *",  # 抽取后15分钟
    config={"input_format": "json", "output_format": "csv"}
)

# 创建管道
extract_id = client.create_task(extract_task).task_id
transform_id = client.create_task(transform_task).task_id
```

### 2. 监控告警
```python
# 系统监控任务
monitor_task = create_http_task(
    name="系统监控",
    url="http://monitoring.example.com/metrics",
    cron_expression="*/10 * * * *",  # 每10分钟
    config={
        "alert_threshold": 80,
        "notification_webhook": "http://alert.example.com/webhook"
    }
)

monitor_id = client.create_task(monitor_task).task_id
```

### 3. 定期报告
```python
# 报告生成任务
report_task = create_shell_task(
    name="日报生成",
    command="python3 generate_daily_report.py",
    cron_expression="0 9 * * 1-5",  # 工作日上午9点
    config={
        "template": "daily_template.html",
        "recipients": ["team@example.com"],
        "schedule": "0900"
    }
)

report_id = client.create_task(report_task).task_id
```

## 💡 最佳实践

### 1. 任务命名
- 使用描述性名称
- 包含任务用途信息
- 避免特殊字符

### 2. 错误处理
- 总是处理异常
- 记录错误日志
- 提供错误恢复机制

### 3. 资源管理
- 合理设置超时时间
- 避免长时间运行任务
- 监控资源使用情况

### 4. 安全考虑
- 不要在配置中存储敏感信息
- 使用环境变量管理密钥
- 定期轮换API密钥

这些示例展示了TaskScheduler微服务组件的主要功能和使用方法，帮助您快速上手并应用到实际项目中。