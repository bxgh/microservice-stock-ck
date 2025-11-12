# microservice-stock

基于事件驱动架构的微服务任务调度系统，支持实时数据处理和监控。

## 快速开始

```bash
# 克隆项目
git clone <repository-url>
cd microservice-stock

# 启动开发环境
./scripts/start-dev.sh

# 构建所有服务
./scripts/build.sh
```

## 架构概览

本项目采用微服务架构，包含以下核心服务：

- **API Gateway** - 统一入口和路由分发
- **TaskScheduler** - 任务调度引擎
- **DataCollector** - 数据采集服务
- **DataProcessor** - 数据处理服务
- **DataStorage** - 数据存储服务
- **Notification** - 通知服务
- **Monitor** - 监控服务
- **Web UI** - 管理界面

详细架构文档请参见 [docs/architecture/](./docs/architecture/)

## 开发指南

### 环境要求

- Python 3.11+
- Node.js 18+
- Docker 24.0+
- Docker Compose 2.20+

### 开发环境设置

1. 复制环境变量模板：`cp .env.example .env`
2. 配置数据库连接和代理设置
3. 启动基础服务：`docker-compose -f infrastructure/docker-compose.yml up -d`
4. 启动开发环境：`./scripts/start-dev.sh`

## 部署

### 开发环境
```bash
docker-compose -f infrastructure/docker-compose.yml up
```

### 生产环境
```bash
docker-compose -f infrastructure/docker-compose.prod.yml up -d
```

## 许可证

MIT License