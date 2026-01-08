# microservice-stock

基于事件驱动架构的微服务任务调度系统，支持实时数据处理和监控。

## 🏗️ Monorepo架构

本项目采用 **Monorepo** 架构，统一管理前后端应用和共享组件：

```
microservice-stock/
├── 📁 apps/                    # 前端应用
│   ├── 🚀 task-scheduler-ui/   # Task Scheduler专用前端
│   └── 🌐 frontend-web/        # 通用Web前端
├── 📁 packages/                # 共享包
│   ├── 🧩 ui-components/       # 共享UI组件库
│   ├── 🔧 utils/               # 工具函数库
│   └── 📝 types/               # TypeScript类型定义
├── 📁 services/                # 后端微服务
│   ├── ⚙️ task-scheduler/      # 任务调度服务
│   ├── 📊 data-collector/      # 数据采集服务
│   └── 🌐 api-gateway/         # API网关
├── 📁 infrastructure/          # 基础设施
├── 📁 docs/                    # 项目文档
└── 📁 tools/                   # 开发工具
```

## 🚀 快速开始

### 启动开发环境
```bash
# 克隆项目
git clone <repository-url>
cd microservice-stock

# 启动基础设施服务
docker-compose -f infrastructure/docker-compose.yml up -d

# 启动后端服务
./scripts/start-dev.sh

# 启动前端应用
cd apps/task-scheduler-ui && npm install && npm run dev
cd apps/frontend-web && npm install && npm run dev
```

### 前端应用开发
```bash
# Task Scheduler UI (任务调度专用)
cd apps/task-scheduler-ui
npm install
npm run dev        # 开发服务器: http://localhost:3000
npm run build      # 构建生产版本

# Frontend Web (通用Web前端)
cd apps/frontend-web
npm install
npm run dev        # 开发服务器: http://localhost:3001
npm run build      # 构建生产版本
```

### 共享组件开发
```bash
# UI组件库
cd packages/ui-components
npm install
npm run dev        # 开发模式（监听变化）
npm run build      # 构建组件库
```

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

MIT License# Test sync from 41
# Test hook Thu Jan  8 12:07:45 PM CST 2026
# Final verification Thu Jan  8 12:08:27 PM CST 2026
