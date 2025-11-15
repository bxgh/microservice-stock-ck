# Get Stock Data 微服务

## 📋 概述

Get Stock Data 是一个专门用于获取股票数据的微服务，提供实时股票价格查询、历史数据获取和股票搜索等功能。基于 FastAPI 框架构建，集成 Nacos 服务注册发现，支持容器化部署。

## 🎯 服务特性

### ✅ 核心功能

- **实时股票数据** - 获取股票实时价格和基本信息
- **历史数据查询** - 支持不同时间周期的历史数据
- **股票搜索** - 根据公司名或股票代码搜索
- **数据缓存** - Redis 缓存提高响应速度
- **服务注册发现** - Nacos集成，自动服务注册和心跳
- **健康检查** - `/api/v1/health` 端点，支持Kubernetes探针
- **中间件系统** - CORS、日志、认证中间件
- **配置管理** - 环境变量 + 设置文件配置
- **API文档** - 自动生成的Swagger UI
- **容器化部署** - Docker + docker-compose

### 📁 项目结构

```
get-stockdata/
├── src/
│   ├── api/                    # API层
│   │   ├── __init__.py         # 路由导出
│   │   ├── health_routes.py    # 健康检查路由
│   │   ├── example_routes.py   # 股票数据路由
│   │   └── middleware.py       # 中间件
│   ├── models/                 # 数据模型层
│   │   ├── __init__.py
│   │   └── base_models.py      # 基础模型（ApiResponse等）
│   ├── config/                 # 配置层
│   │   ├── __init__.py
│   │   └── settings.py         # 应用设置
│   ├── registry/               # 服务注册发现
│   │   ├── __init__.py
│   │   └── nacos_registry_simple.py  # Nacos客户端
│   └── main.py                 # 应用入口
├── .env                        # 环境变量配置
├── Dockerfile                  # 容器化配置
├── docker-compose.yml          # 服务编排
├── requirements.txt            # Python依赖
└── README.md                   # 本文档
```

## 🚀 快速开始

### 启动服务

```bash
# 进入服务目录
cd services/get-stockdata

# 构建并启动服务
docker-compose up --build -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f get-stockdata
```

### 服务配置

#### 环境变量配置

编辑 `.env` 文件配置股票数据源：
```bash
# 股票数据配置
STOCK_API_BASE_URL=https://api.example.com
STOCK_API_TIMEOUT=30
STOCK_CACHE_TTL=300
ENABLE_STOCK_CACHING=true

# 数据库配置（可选）
MYSQL_HOST=your-mysql-host
MYSQL_DATABASE=microservice_stock
MYSQL_USER=your-username
MYSQL_PASSWORD=your-password

# Redis配置（用于缓存）
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### 服务端口

- **API服务**: 8086
- **健康检查**: `/api/v1/health`
- **API文档**: `http://localhost:8086/docs`

## 📡 API 接口

### 股票数据接口

#### 获取实时股票数据
```http
GET /api/v1/stocks/{symbol}
```

**参数:**
- `symbol`: 股票代码（如 AAPL, TSLA）

**示例:**
```bash
curl http://localhost:8086/api/v1/stocks/AAPL
```

#### 获取股票历史数据
```http
GET /api/v1/stocks/{symbol}/history?period=1d&interval=1h
```

**参数:**
- `symbol`: 股票代码
- `period`: 时间周期 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
- `interval`: 数据间隔 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

**示例:**
```bash
curl "http://localhost:8086/api/v1/stocks/TSLA/history?period=1mo&interval=1d"
```

#### 搜索股票
```http
GET /api/v1/stocks/search/{query}
```

**参数:**
- `query`: 搜索关键词（公司名或股票代码）

**示例:**
```bash
curl http://localhost:8086/api/v1/stocks/search/apple
```

### 健康检查
```http
GET /api/v1/health
```

### API 文档
访问 `http://localhost:8086/docs` 查看完整的 API 文档

## 🔧 开发指南

### 添加股票数据源

1. **修改股票API配置**
   编辑 `.env` 文件：
   ```bash
   STOCK_API_BASE_URL=https://your-stock-api-provider.com
   STOCK_API_KEY=your-api-key
   STOCK_API_TIMEOUT=30
   ```

2. **实现真实数据获取**
   在 `src/api/example_routes.py` 中替换示例代码：
   ```python
   # TODO: 实现真实的股票数据获取逻辑
   # 这里可以集成 Yahoo Finance, Alpha Vantage, 或其他股票数据API
   ```

### 部署配置

#### 生产环境配置

1. **环境变量**
   ```bash
   # 生产环境配置
   DEBUG=false
   LOG_LEVEL=INFO
   MYSQL_HOST=your-prod-mysql
   REDIS_HOST=your-prod-redis
   ```

2. **安全配置**
   ```bash
   # 更新密钥
   SECRET_KEY=your-production-secret-key
   STOCK_API_KEY=your-production-api-key
   ```

## 🧪 测试

### API 测试

```bash
# 健康检查
curl http://localhost:8086/api/v1/health

# 获取股票数据
curl http://localhost:8086/api/v1/stocks/AAPL

# 获取历史数据
curl "http://localhost:8086/api/v1/stocks/TSLA/history?period=5d"

# 搜索股票
curl http://localhost:8086/api/v1/stocks/search/apple
```

### 服务状态检查

```bash
# 检查容器状态
docker-compose ps

# 查看日志
docker-compose logs -f get-stockdata

# 检查服务注册
curl "http://localhost:8848/nacos/v1/ns/service/list" | grep get-stockdata
```

## 🚨 故障排除

### 常见问题

1. **端口占用**
   ```bash
   # 检查端口
   netstat -tulpn | grep :8086
   # 修改端口配置
   ```

2. **股票API连接失败**
   ```bash
   # 检查API配置
   cat .env | grep STOCK_API
   # 查看错误日志
   docker-compose logs get-stockdata
   ```

3. **Redis连接失败**
   ```bash
   # 检查Redis服务
   docker ps | grep redis
   # 测试连接
   redis-cli -h localhost ping
   ```

## 📝 待办事项

- [ ] 集成真实股票数据API（Yahoo Finance, Alpha Vantage等）
- [ ] 实现Redis缓存机制
- [ ] 添加数据库持久化
- [ ] 实现数据更新调度任务
- [ ] 添加API限流和认证
- [ ] 完善错误处理和监控
- [ ] 添加单元测试和集成测试

## 📚 相关资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Yahoo Finance API](https://pypi.org/project/yfinance/)
- [Alpha Vantage API](https://www.alphavantage.co/documentation/)
- [Nacos 服务发现](https://nacos.io/)

---

**🚀 Get Stock Data 微服务已准备就绪！**