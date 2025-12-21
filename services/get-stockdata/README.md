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
- **混合架构支持** - 整合本地 (Mootdx) 与云端 (AkShare/BaoStock) 数据源，通过专用代理实现 100% 连通性

### 🌐 网络与混合架构 (重要)
本项目采用 **混合数据源架构**，确保高性能与稳定性：
- **本地源 (Mootdx)**: 实时分笔数据，通过 TCP 直连。
- **云端源 (124.221.80.250)**: 股票词典、历史数据、实时热榜。
- **容器网络**: 必须启用 `network_mode: host`。
- **云端代理**: 统一使用内网网关 `http://192.168.151.18:3128`。

### 📁 项目结构

```
get-stockdata/
├── src/                        # 源代码
│   ├── api/                    # API层
│   ├── core/                   # 核心业务逻辑
│   ├── config/                 # 配置层
│   ├── data_sources/           # 数据源适配器
│   ├── models/                 # 数据模型
│   ├── services/               # 业务服务
│   ├── utils/                  # 工具类
│   └── main.py                 # 应用入口
├── docs/                       # 文档中心
│   ├── architecture/           # 架构文档
│   ├── guides/                 # 使用指南
│   ├── plans/                  # 开发计划
│   ├── reports/                # 各种报告
│   └── src/                    # 源码文档
├── tests/                      # 测试套件
│   ├── performance/            # 性能测试
│   └── ...                     # 单元测试
├── config/                     # 配置文件模板
├── .dev-environment            # 开发环境提示
├── CONTRIBUTING.md             # 贡献指南
├── DEVELOPER_DISCOVERY.md      # 开发者发现机制
├── DEV_ENVIRONMENT_SETUP.md    # 环境搭建说明
├── Dockerfile                  # 容器构建
├── Makefile                    # 常用命令
├── README.md                   # 项目总览
├── docker-compose.dev.yml      # 开发环境编排
├── docker-compose.yml          # 生产环境编排
├── requirements.txt            # Python依赖
└── start.sh                    # 启动脚本
```

## 🔥 开发者必读

> **⚠️ 开发人员请注意**: 本项目支持热加载开发环境！修改代码后自动生效，无需重启容器！

### 🚀 开发环境快速启动

```bash
# ✅ 推荐：使用开发环境（支持热加载）
cd services/get-stockdata
docker compose -f docker-compose.dev.yml up

# 修改代码后，等待 1-2 秒自动生效！
```

**开发环境特性**:
- ✅ **热加载**: 修改 Python 代码后 1-2 秒自动重启
- ✅ **实时调试**: DEBUG 级别日志，详细输出
- ✅ **快速迭代**: 无需重启容器，开发效率提升 90%

详细文档请查看: [热加载使用指南](./docs/guides/HOT_RELOAD_GUIDE.md)

---

## 🚀 快速开始

### 启动服务

```bash
# 进入服务目录
cd services/get-stockdata

# 构建并启动服务
docker compose up --build -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f get-stockdata
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

## ⚙️ 核心组件

### 🚀 Fenbi Engine (分笔数据引擎)

高性能的分笔数据处理引擎，专为处理大规模 Tick 数据设计。经过深度优化，在保证数据完整性的前提下实现了极高的处理效率。

**核心特性:**
- **⚡ 高性能处理**: 优化后的数据管道，10万条数据处理仅需 **~1.05秒** (较优化前提升60%)
- **🔄 智能去重**: 内置 `DataDeduplicator`，支持多种策略（First/Last/Random）的数据去重
- **⏱️ 精准排序**: 内置 `TimeFormatter`，支持混合时间格式的高效排序
- **📊 统计分析**: 内置 `StatisticsGenerator`，自动生成包含价格分布、成交量分析的详细报告
- **🛡️ 数据完整性**: 采用索引映射技术，确保原始数据对象 100% 完整无损

**Python 调用示例:**

```python
from src.services.fenbi_engine import FenbiEngine

# 初始化引擎
engine = FenbiEngine()

# 1. 获取并处理数据 (自动执行: 获取 -> 排序 -> 去重)
data = await engine.get_tick_data(
    symbol='000001', 
    date='20250101',
    enable_time_sort=True,      # 启用时间排序
    enable_deduplication=True   # 启用数据去重
)

# 2. 获取处理统计
stats = engine.get_stats()
print(f"处理耗时: {stats['duration']}s, 去重: {stats['duplicates_removed']}条")

# 3. 生成增强分析报告
report = engine.generate_enhanced_report(data)
print(f"价格波动: {report['data_characteristics']['price_stats']}")
```

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
docker compose ps

# 查看日志
docker compose logs -f get-stockdata

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
   docker compose logs get-stockdata
   ```

3. **Redis连接失败**
   ```bash
   # 检查Redis服务
   docker ps | grep redis
   # 测试连接
   redis-cli -h localhost ping
   ```

## �️ 项目路线图

我们有详细的开发计划，包括数据源集成、缓存机制、持久化存储等。

👉 **查看详细规划**: [ROADMAP.md](./docs/plans/ROADMAP.md)

**近期重点:**
- [ ] 集成真实股票数据API
- [ ] 实现Redis缓存机制
- [ ] 添加数据库持久化

## 📚 相关资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Yahoo Finance API](https://pypi.org/project/yfinance/)
- [Alpha Vantage API](https://www.alphavantage.co/documentation/)
- [Nacos 服务发现](https://nacos.io/)

---

**🚀 Get Stock Data 微服务已准备就绪！**