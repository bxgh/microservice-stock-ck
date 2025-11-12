# TaskScheduler 微服务

TaskScheduler 是 microservice-stock 项目的核心调度服务，负责任务的定义、调度和执行管理。

## 🚀 快速开始

### 开发环境运行

```bash
# 1. 进入服务目录
cd services/task-scheduler

# 2. 复制环境变量文件
cp .env.example .env

# 3. 编辑环境变量
vim .env

# 4. 安装依赖
pip install -r requirements.txt

# 5. 运行服务
python src/app.py
```

### Docker 运行

```bash
# 构建镜像
docker build -t microservice-stock/task-scheduler:latest .

# 运行容器
docker run -p 8080:8080 --env-file .env microservice-stock/task-scheduler:latest
```

## 📋 服务信息

- **服务地址**: http://localhost:8080
- **API 文档**: http://localhost:8080/docs
- **健康检查**: http://localhost:8080/api/v1/health

## 🏗️ 架构设计

### 分层架构

```
src/
├── api/           # API 层 - HTTP 路由和请求处理
├── service/       # 业务层 - 业务逻辑处理
├── repository/    # 数据层 - 数据访问抽象
├── models/        # 模型层 - 数据模型定义
├── config/        # 配置层 - 配置管理
├── plugins/       # 插件层 - 插件系统
└── app.py         # 应用入口
```

### 核心功能

- ✅ **任务管理**: 任务的创建、更新、删除、查询
- ✅ **调度引擎**: 支持 cron 表达式和间隔调度
- ✅ **执行管理**: 任务执行记录和状态跟踪
- ✅ **插件系统**: 可扩展的插件架构
- ✅ **监控健康**: 服务健康检查和指标监控
- ✅ **异步处理**: 基于 FastAPI 的异步架构

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `APP_NAME` | 应用名称 | TaskScheduler |
| `HOST` | 服务主机 | 0.0.0.0 |
| `PORT` | 服务端口 | 8080 |
| `LOG_LEVEL` | 日志级别 | INFO |
| `MYSQL_HOST` | MySQL 主机 | - |
| `REDIS_HOST` | Redis 主机 | localhost |
| `CLICKHOUSE_HOST` | ClickHouse 主机 | localhost |
| `SECRET_KEY` | 安全密钥 | - |

### 数据库配置

服务需要以下数据库：

1. **MySQL 5.7** - 存储任务元数据
2. **Redis** - 缓存和消息队列
3. **ClickHouse** - 时序数据存储

## 📚 API 文档

### 健康检查

```http
GET /api/v1/health
```

### 任务管理

```http
# 获取任务列表
GET /api/v1/tasks

# 创建任务
POST /api/v1/tasks

# 获取任务详情
GET /api/v1/tasks/{task_id}

# 启动任务
POST /api/v1/tasks/{task_id}/start

# 停止任务
POST /api/v1/tasks/{task_id}/stop
```

详细 API 文档请访问: http://localhost:8080/docs

## 🔍 开发指南

### 添加新功能

1. 在 `models/` 中定义数据模型
2. 在 `repository/` 中实现数据访问
3. 在 `service/` 中实现业务逻辑
4. 在 `api/` 中添加路由

### 插件开发

1. 继承 `plugins/base_plugin.py` 中的 `BasePlugin`
2. 实现必要的方法
3. 在 `plugins/plugin_manager.py` 中注册插件

### 测试

```bash
# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=src tests/
```

## 📦 部署

### Docker Compose

```bash
# 在项目根目录运行
docker-compose up -d task-scheduler
```

### 生产环境

1. 设置环境变量
2. 确保数据库可访问
3. 运行服务容器
4. 配置负载均衡（可选）

## 🔍 监控

### 健康检查

服务提供以下健康检查端点：

- `/api/v1/health` - 基础健康检查
- `/metrics` - Prometheus 指标（如果启用）

### 日志

日志文件位置：

- `logs/taskscheduler.log` - 标准日志
- `logs/taskscheduler.json` - JSON 格式日志

## 🤝 贡献

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

MIT License