# Components

## TaskScheduler Service (核心调度服务)

**Responsibility:** 任务调度引擎，负责任务的生命周期管理、调度策略执行和工作流编排

**Key Interfaces:**
- `POST /api/v1/tasks` - 创建任务
- `GET /api/v1/tasks/{id}` - 查询任务
- `POST /api/v1/tasks/{id}/start` - 启动任务
- `POST /api/v1/tasks/{id}/stop` - 停止任务
- Redis 消息订阅：`task.schedule.*` - 接收调度事件
- Redis 消息发布：`task.execution.*` - 发布执行事件

**Dependencies:** Redis (消息队列), MySQL (元数据存储)
**Technology Stack:** Python 3.11+, FastAPI 0.104+, Celery (异步任务), APScheduler (调度器)

## DataCollector Service (数据采集服务)

**Responsibility:** 连接外部数据源，执行数据采集适配，管理连接池，执行数据质量校验

**Key Interfaces:**
- `POST /api/v1/datasources` - 创建数据源
- `GET /api/v1/datasources/{id}/health` - 数据源健康检查
- `POST /api/v1/collection/start` - 启动数据采集
- Redis 消息发布：`data.collected.*` - 发布采集完成事件

**Dependencies:** Redis (消息队列), 外部数据源 (数据库/API/文件)
**Technology Stack:** Python 3.11+, FastAPI 0.104+, SQLAlchemy (数据库连接), aiohttp (HTTP 客户端)

## Monitor Service (监控服务)

**Responsibility:** 服务健康监控，性能指标收集，链路追踪分析，日志聚合处理

**Key Interfaces:**
- `GET /api/v1/system/health` - 系统健康检查
- `GET /api/v1/system/metrics` - 系统性能指标
- `GET /api/v1/logs` - 日志查询
- Redis 消息订阅：`*.events.*` - 接收所有服务事件

**Dependencies:** Redis (消息队列), 本地文件系统 (日志存储)
**Technology Stack:** Python 3.11+, FastAPI 0.104+, psutil (系统监控), 自定义日志收集器

## API Gateway (API 网关)

**Responsibility:** 统一入口，路由分发，负载均衡，协议转换

**Key Interfaces:**
- 所有外部请求的统一入口点
- 路由规则：`/api/v1/tasks/*` → TaskScheduler, `/api/v1/data/*` → DataCollector/DataProcessor/DataStorage, `/api/v1/system/*` → Monitor
- 静态文件服务：Web UI 界面

**Dependencies:** 所有后端服务
**Technology Stack:** Nginx 1.24+, 配置文件驱动的路由规则

## Web UI (管理界面)

**Responsibility:** 任务管理界面，系统监控面板，数据可视化

**Key Interfaces:**
- 前端路由：`/tasks` - 任务管理页面
- 前端路由：`/dashboard` - 监控仪表板
- API 客户端：调用所有后端服务的 REST API

**Dependencies:** API Gateway, 所有后端服务 API
**Technology Stack:** React 18.2+, TypeScript 5.0+, Ant Design 5.0+, Zustand 4.4+, Vite 5.0+
