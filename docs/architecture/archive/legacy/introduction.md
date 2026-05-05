# Introduction

基于你的项目背景和约束条件，这是一个：

- **开发环境：** 个人开发者，内网环境，代理 192.168.151.18:3128
- **服务器配置：** 10G CPU, 64GB 内存, 100GB 硬盘
- **架构组成：** TaskScheduler 微服务 + Web UI 管理界面 + API Gateway
- **技术栈：** Python + Redis + ClickHouse (实时数据) + MySQL 5.7 (外部数据库)
- **部署方式：** Docker Compose (MVP 方式，避免过度拆分)
- **简化配置：** 无 API 认证，单租户，轻量级日志方案
- **消息格式：** JSON
- **架构原则：** 事件驱动，服务解耦，容器化部署

**MVP 服务拆分策略：**
1. **API Gateway** - 统一入口，路由分发
2. **TaskScheduler Service** - 核心调度逻辑
3. **Web UI** - 管理界面
4. **ClickHouse** - 实时数据存储
5. **共享基础设施：** Redis, MySQL 5.7, 轻量级日志

**详细理由：**
- 选择 Docker Compose 而非 Kubernetes，适合个人开发和资源约束
- API Gateway 独立部署，为未来扩展做准备
- ClickHouse 专注实时数据，MySQL 5.7 处理持久化元数据
- MVP 拆分避免过度工程化，适合个人开发节奏
