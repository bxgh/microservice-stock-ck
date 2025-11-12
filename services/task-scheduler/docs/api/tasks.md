# 任务管理接口文档

## 📋 任务定义

### 基础字段
- `name`: 任务名称 (必填)
- `task_type`: 任务类型 (必填)
- `description`: 任务描述 (可选)
- `enabled`: 是否启用 (默认true)

### 调度配置
- `cron_expression`: Cron表达式
- `interval_seconds`: 间隔秒数
- `start_date`: 开始时间
- `end_date`: 结束时间

### 执行配置
- `timeout`: 超时时间(秒)
- `max_retries`: 最大重试次数
- `retry_delay`: 重试延迟(秒)
- `config`: 任务配置字典
- `tags`: 标签列表

## 🎯 接口详情

### 1. 创建任务

**请求**:
- 方法: POST
- 路径: `/tasks`
- Body: TaskDefinition对象

**响应**:
- 状态码: 201 (成功创建)
- 数据: 创建的任务信息

**示例**:
```json
{
  "name": "健康检查",
  "task_type": "http_request",
  "cron_expression": "*/5 * * * *",
  "timeout": 30,
  "config": {
    "url": "http://example.com/health",
    "method": "GET"
  }
}
```

### 2. 查询任务列表

**请求**:
- 方法: GET
- 路径: `/tasks`

**查询参数**:
- `page`: 页码 (默认1)
- `page_size`: 每页数量 (默认20)
- `status`: 状态过滤
- `tags`: 标签过滤 (逗号分隔)

**响应**:
- 状态码: 200
- 数据: 分页任务列表

**状态值**:
- `pending`: 等待执行
- `running`: 正在执行
- `success`: 执行成功
- `failed`: 执行失败
- `cancelled`: 已取消
- `paused`: 已暂停

### 3. 获取任务详情

**请求**:
- 方法: GET
- 路径: `/tasks/{task_id}`

**响应**:
- 状态码: 200 (成功)
- 数据: 完整任务信息
- 包含最近执行记录

### 4. 更新任务

**请求**:
- 方法: PUT
- 路径: `/tasks/{task_id}`
- Body: 更新的TaskDefinition对象

**响应**:
- 状态码: 200 (更新成功)
- 数据: 更新后的任务信息

### 5. 删除任务

**请求**:
- 方法: DELETE
- 路径: `/tasks/{task_id}`

**响应**:
- 状态码: 200 (删除成功)
- 数据: 操作结果

## 🎮 任务控制

### 手动触发
- 方法: POST
- 路径: `/tasks/{task_id}/trigger`
- 说明: 立即执行任务

### 暂停任务
- 方法: POST
- 路径: `/tasks/{task_id}/pause`
- 说明: 暂停任务调度

### 恢复任务
- 方法: POST
- 路径: `/tasks/{task_id}/resume`
- 说明: 恢复任务调度

### 启用/禁用
- 方法: POST
- 路径: `/tasks/{task_id}/enable` 或 `/tasks/{task_id}/disable`
- 说明: 改变任务启用状态

## 📊 任务统计

### 获取任务统计
- 方法: GET
- 路径: `/tasks/{task_id}/statistics`
- 查询参数: `days` (统计天数, 默认30)

**统计内容**:
- 总执行次数
- 成功/失败次数
- 成功率
- 平均执行时间
- 最小/最大执行时间

## 🔧 任务类型

### 内置插件
- `http_request`: HTTP请求任务
- `shell_command`: Shell命令任务

### 自定义插件
- 支持插件扩展
- 配置验证
- 错误处理

## ⚠️ 注意事项

### Cron表达式
- 使用标准Cron格式
- 时区基于服务配置
- 支持秒级精度

### 超时处理
- 超时任务标记为失败
- 支持重试机制
- 记录超时日志

### 并发控制
- 默认每个任务最大1个并发实例
- 可配置并发限制
- 队列化执行机制

### 错误处理
- 执行失败自动重试
- 指数退避策略
- 记录详细错误信息