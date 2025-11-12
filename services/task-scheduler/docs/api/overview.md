# API接口概览

## 🌐 基础信息

- **协议**: HTTP/HTTPS
- **格式**: JSON
- **版本**: v1
- **基础URL**: `http://localhost:8080/api/v1`

## 🔐 认证方式

### API Key认证
```http
Authorization: Bearer <your-api-key>
```

### 环境配置
- 开发环境: 可选认证
- 生产环境: 必需认证

## 📋 核心接口分类

### 任务管理接口
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/tasks` | 创建任务 |
| GET | `/tasks` | 查询任务列表 |
| GET | `/tasks/{id}` | 获取任务详情 |
| PUT | `/tasks/{id}` | 更新任务 |
| DELETE | `/tasks/{id}` | 删除任务 |

### 任务控制接口
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/tasks/{id}/trigger` | 手动触发 |
| POST | `/tasks/{id}/pause` | 暂停任务 |
| POST | `/tasks/{id}/resume` | 恢复任务 |
| POST | `/tasks/{id}/enable` | 启用任务 |
| POST | `/tasks/{id}/disable` | 禁用任务 |

### 监控统计接口
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/stats` | 服务统计 |
| GET | `/tasks/{id}/statistics` | 任务统计 |

## 📊 通用响应格式

### 成功响应
```json
{
  "success": true,
  "message": "操作成功",
  "data": { ... },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 错误响应
```json
{
  "success": false,
  "message": "错误描述",
  "data": null,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🎯 主要特性

### 分页支持
- 支持任务列表分页查询
- 可配置每页数量
- 提供总数统计

### 过滤查询
- 按状态过滤任务
- 按标签过滤任务
- 按时间范围过滤

### 错误处理
- 统一错误响应格式
- 详细的错误信息
- HTTP状态码对应

### 数据验证
- 请求参数自动验证
- 任务配置格式检查
- Cron表达式验证

## 🔗 文档链接

- [任务管理详细说明](tasks.md)
- [监控接口说明](monitoring.md)
- [认证授权说明](authentication.md)
- [错误代码说明](error-codes.md)

## 🛠️ 开发工具

### 在线文档
- Swagger UI: `/docs`
- ReDoc: `/redoc`

### 测试工具
- 健康检查: `/api/v1/health`
- 服务统计: `/api/v1/stats`