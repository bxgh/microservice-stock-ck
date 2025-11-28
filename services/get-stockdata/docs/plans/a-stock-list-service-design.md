# A股股票代码客户端服务设计方案 (集成到get-stockdata微服务)

## 🎯 服务目标

基于已发现的A股股票代码数据采集系统API（`http://124.221.80.250:8000/api/v1/stocks`），在get-stockdata微服务中创建一个轻量级、高效、可靠的股票代码客户端服务，为分笔数据获取提供完整的股票基础数据支持。

## 🚀 重要发现：现有API资源

### 可用的A股股票代码API
- **API地址**: `http://124.221.80.250:8000/api/v1/stocks`
- **数据量**: 5,448只A股股票完整覆盖
- **交易所支持**: SH(沪市) + SZ(深市) + BJ(北交所)
- **数据格式**: 标准RESTful API，支持JSON响应

### 现有API功能特性
- ✅ **分页查询**: 支持skip/limit参数
- ✅ **多维度筛选**: exchange(交易所)、security_type(证券类型)、is_active(活跃状态)
- ✅ **模糊搜索**: name_search参数支持股票名称搜索
- ✅ **多格式代码映射**: tushare, akshare, tonghua_shun, wind, east_money
- ✅ **任务管理**: 采集任务状态监控和管理
- ✅ **数据导出**: 支持JSON/CSV格式导出

## 📊 核心需求分析 (基于现有API)

### 功能需求
- **API封装** - 封装外部API调用，提供统一接口
- **缓存优化** - 减少外部API调用，提升响应速度
- **容错机制** - 外部API异常时的降级和重试策略
- **数据适配** - 适配外部API数据格式到内部需求
- **批量处理** - 支持批量获取和处理股票数据

### 非功能需求
- **高性能** - 缓存命中时响应 < 100ms
- **高可用** - 外部API不可用时使用缓存数据
- **数据准确** - 100%使用经过验证的外部数据
- **智能缓存** - 多级缓存策略，减少外部依赖
- **容错处理** - 自动重试 + 降级策略

## 🏗️ 集成架构设计 (get-stockdata微服务)

### 集成方案概述
将股票代码客户端服务作为get-stockdata微服务的一个模块，避免微服务过度拆分，保持业务逻辑的内聚性。

### 核心模块结构
```
get-stockdata微服务
├── src/
│   ├── services/
│   │   ├── stock_code_client.py        # 股票代码客户端 (新增)
│   │   ├── tick_data_service.py        # 分笔数据服务 (扩展)
│   │   └── batch_processor.py          # 批量处理器 (新增)
│   ├── api/
│   │   ├── stock_code_routes.py        # 股票代码API (新增)
│   │   ├── tick_data_routes.py         # 分笔数据API (扩展)
│   │   └── middleware.py               # 中间件 (现有)
│   ├── models/
│   │   ├── stock_models.py             # 股票数据模型 (新增)
│   │   ├── tick_models.py              # 分笔数据模型 (新增)
│   │   └── base_models.py              # 基础模型 (现有)
│   ├── config/
│   │   └── settings.py                 # 配置管理 (扩展)
│   └── main.py                         # 应用入口 (现有)
```

### 股票代码客户端模块结构
```
StockCodeClient (模块)
├── 客户端层 (Client Layer)
│   ├── 外部API客户端
│   ├── HTTP请求封装
│   └── 连接池管理
├── 缓存层 (Cache Layer)
│   ├── Redis缓存 (热数据)
│   ├── 内存缓存 (配置数据)
│   └── 缓存策略管理
├── 容错层 (Resilience Layer)
│   ├── 自动重试机制
│   ├── 熔断器
│   └── 降级策略
├── 适配层 (Adapter Layer)
│   ├── 数据格式转换
│   ├── 接口适配
│   └── 错误处理
└── 服务层 (Service Layer)
    ├── 股票查询服务
    ├── 批量处理服务
    └── 缓存管理服务
```

### 架构优势
- 🎯 **业务内聚**: 股票代码和分笔数据统一管理
- ⚡ **高性能**: 内部调用比服务间调用更快
- 🛡️ **资源共享**: 共享缓存、数据库、监控等基础设施
- 🔧 **简化运维**: 单个服务，简化部署和维护
- 💰 **成本效益**: 避免微服务过度拆分带来的复杂性

## 📋 详细功能设计 (基于现有API)

### 1. 外部API客户端模块

#### 1.1 HTTP客户端封装
- **连接池管理** - 复用HTTP连接，提升性能
- **请求封装** - 统一的请求格式和参数处理
- **响应处理** - 统一的响应解析和错误处理
- **超时控制** - 合理的请求超时设置

#### 1.2 API接口映射
```python
# 主要API端点映射
GET /api/v1/stocks                    # 获取股票列表
GET /api/v1/stocks/{standard_code}    # 获取单只股票详情
GET /api/v1/stocks/exchanges          # 获取交易所列表
GET /api/v1/stocks/export             # 导出股票数据
GET /api/v1/data-sources/status       # 数据源状态
```

#### 1.3 参数适配
- **筛选参数** - exchange, security_type, is_active, name_search
- **分页参数** - skip, limit
- **导出参数** - format (json/csv)
- **缓存键生成** - 基于参数生成唯一缓存键

### 2. 数据适配模块

#### 2.1 数据格式转换
- **外部API格式 → 内部格式**
  - standard_code → stock_code (统一字段名)
  - formats → code_mappings (多格式代码映射)
  - exchange → exchange_code (交易所编码)
  - security_type → asset_type (资产类型)

#### 2.2 数据结构适配
```python
# 外部API响应格式
{
    "standard_code": "000001",
    "name": "平安银行",
    "exchange": "SZ",
    "security_type": "stock",
    "is_active": true,
    "formats": {
        "standard": "000001",
        "tushare": "000001.SZ",
        "akshare": "000001",
        "tonghua_shun": "000001.SZ",
        "wind": "000001.SZ",
        "east_money": "000001"
    }
}

# 内部使用格式
{
    "stock_code": "000001",
    "stock_name": "平安银行",
    "exchange": "SZ",
    "asset_type": "stock",
    "is_active": true,
    "code_mappings": {
        "tushare": "000001.SZ",
        "akshare": "000001",
        "tonghua_shun": "000001.SZ",
        "wind": "000001.SZ",
        "east_money": "000001"
    }
}
```

#### 2.3 交易所代码映射
- **SH** → Shanghai Stock Exchange (上交所)
- **SZ** → Shenzhen Stock Exchange (深交所)
- **BJ** → Beijing Stock Exchange (北交所)

### 3. 缓存设计

#### 3.1 多级缓存策略
- **L1缓存** - 内存缓存 (Python dict，最快访问)
  - 缓存时间: 10分钟
  - 存储热点股票列表 (Top 100)
  - 存储交易所列表等静态数据

- **L2缓存** - Redis缓存 (分布式缓存)
  - 缓存时间: 30分钟
  - 存储完整的股票列表 (5,448只)
  - 支持按交易所、类型分类缓存

- **L3缓存** - 本地文件缓存 (持久化缓存)
  - 缓存时间: 24小时
  - 存储导出的完整数据文件
  - 外部API不可用时的降级数据源

#### 3.2 缓存键设计
```
# 股票列表缓存键
stocks:all                          # 全市场股票列表
stocks:exchange:SH                  # 沪市股票列表
stocks:exchange:SZ                  # 深市股票列表
stocks:exchange:BJ                  # 北交所股票列表
stocks:search:{query}               # 搜索结果缓存

# 单只股票缓存键
stock:{stock_code}                  # 单只股票详情
stock:{stock_code}:mappings         # 代码映射信息

# 统计数据缓存键
stats:total_count                   # 股票总数统计
stats:exchange_count                # 各交易所股票统计
```

#### 3.3 缓存更新策略
- **主动更新** - 定时任务刷新缓存
- **被动更新** - 缓存过期时自动更新
- **手动刷新** - 提供缓存刷新接口

### 4. 服务接口设计 (集成到get-stockdata微服务)

#### 4.1 核心服务接口 (stock_code_client.py)
```python
class StockCodeClient:
    """股票代码客户端服务"""

    async def get_all_stocks(self, limit: int = 1000) -> List[StockInfo]:
        """获取全市场股票列表"""

    async def get_stocks_by_exchange(self, exchange: str) -> List[StockInfo]:
        """按交易所获取股票列表"""

    async def search_stocks(self, query: str) -> List[StockInfo]:
        """股票搜索"""

    async def get_stock_detail(self, stock_code: str) -> StockInfo:
        """获取单只股票详情"""

    async def filter_stocks(self, filters: dict) -> List[StockInfo]:
        """按条件筛选股票"""

    async def get_stock_mappings(self, stock_code: str) -> dict:
        """获取股票代码映射 (用于通达信查询)"""
```

#### 4.2 批量处理接口 (batch_processor.py)
```python
class BatchStockProcessor:
    """批量股票处理器"""

    async def get_batch_stocks(self, stock_codes: List[str]) -> List[StockInfo]:
        """批量获取股票信息"""

    async def get_all_stocks_paginated(self, page_size: int = 1000) -> AsyncIterator[List[StockInfo]]:
        """分页获取全市场股票 (供分笔数据批量处理使用)"""

    async def get_stocks_for_tick_data(self, exchange: str = None, limit: int = None) -> List[StockInfo]:
        """获取需要获取分笔数据的股票列表"""
```

#### 4.3 缓存管理接口
```python
class CacheManager:
    """缓存管理器"""

    async def refresh_cache(self, cache_type: str = "all") -> bool:
        """刷新缓存"""

    async def get_cache_status(self) -> dict:
        """获取缓存状态"""

    async def clear_cache(self, pattern: str = None) -> bool:
        """清理缓存"""
```

#### 4.4 REST API接口 (stock_code_routes.py)
```python
# 股票代码相关API接口
GET /api/v1/stocks/list                    # 获取股票列表
GET /api/v1/stocks/{code}/detail          # 获取股票详情
GET /api/v1/stocks/{code}/mappings        # 获取代码映射
GET /api/v1/stocks/exchange/{exchange}    # 按交易所获取股票
GET /api/v1/stocks/search                 # 股票搜索
POST /api/v1/stocks/batch                  # 批量获取股票信息
GET /api/v1/stocks/export                 # 导出股票数据
GET /api/v1/stocks/cache/status           # 缓存状态
POST /api/v1/stocks/cache/refresh         # 刷新缓存

# 内部接口 (供分笔数据服务内部调用)
GET /internal/stocks/list                  # 获取股票列表 (内部)
GET /internal/stocks/{code}/mappings       # 获取代码映射 (内部)
GET /internal/stocks/exchange/{exchange}/list  # 按交易所获取列表 (内部)
```

### 5. 容错和性能优化

#### 5.1 容错机制
- **自动重试** - 请求失败时自动重试 (最多3次)
- **熔断器** - 连续失败时暂停请求，保护系统
- **降级策略** - 外部API不可用时使用缓存数据
- **超时控制** - 合理的请求超时设置 (5秒)

#### 5.2 性能优化
- **连接复用** - HTTP连接池，避免频繁建连
- **并发请求** - 支持批量并发获取股票数据
- **数据预加载** - 服务启动时预加载热点数据
- **内存优化** - 合理控制缓存大小，避免内存溢出

#### 5.3 监控指标
- **API响应时间** - 外部API调用延迟监控
- **缓存命中率** - 各级缓存的命中率统计
- **错误率监控** - API调用失败率监控
- **可用性监控** - 服务可用性实时监控

### 6. 配置和部署

#### 6.1 配置管理
```python
# 外部API配置
STOCK_API_BASE_URL = "http://124.221.80.250:8000"
STOCK_API_TIMEOUT = 5.0
STOCK_API_RETRY_COUNT = 3

# 缓存配置
REDIS_HOST = "localhost"
REDIS_PORT = 6379
CACHE_TTL_MEMORY = 600      # 10分钟
CACHE_TTL_REDIS = 1800      # 30分钟
CACHE_TTL_FILE = 86400      # 24小时

# 性能配置
MAX_CONCURRENT_REQUESTS = 10
CONNECTION_POOL_SIZE = 20
REQUEST_TIMEOUT = 5.0
```

#### 6.2 集成部署架构
```
get-stockdata微服务 (单一服务)
├── 股票代码模块 (StockCodeClient)
│   ├── 外部API集成 (124.221.80.250:8000)
│   ├── 多级缓存 (Redis + 内存 + 文件)
│   └── 容错机制 (重试 + 熔断 + 降级)
├── 分笔数据模块 (TickDataService)
│   ├── TongDaXin集成
│   ├── 100%成功策略引擎
│   └── 批量处理调度器
├── API路由层
│   ├── 股票代码API (/api/v1/stocks/*)
│   ├── 分笔数据API (/api/v1/ticks/*)
│   └── 内部接口 (/internal/*)
└── 共享基础设施
    ├── Redis缓存
    ├── MySQL数据库
    ├── 配置管理
    └── 监控日志
```

#### 6.3 微服务集成优势
- **业务内聚**: 股票基础数据 + 分笔数据统一管理
- **性能优化**: 内部调用比HTTP服务间调用快10-100倍
- **资源共享**: 共享缓存、数据库连接池、监控等
- **简化运维**: 单一服务部署，减少运维复杂性
- **成本效益**: 避免多个微服务带来的资源开销

#### 6.4 环境变量配置
```bash
# 外部股票API配置
EXTERNAL_STOCK_API_URL=http://124.221.80.250:8000
EXTERNAL_STOCK_API_TIMEOUT=5
EXTERNAL_STOCK_API_RETRY_COUNT=3

# 缓存配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
CACHE_TTL_MEMORY=600      # 10分钟
CACHE_TTL_REDIS=1800      # 30分钟
CACHE_TTL_FILE=86400      # 24小时

# 服务配置
LOG_LEVEL=INFO
MAX_WORKERS=4
ENABLE_CACHE=true

# 性能配置
MAX_CONCURRENT_REQUESTS=10
CONNECTION_POOL_SIZE=20
REQUEST_TIMEOUT=5.0
```

## 🔄 数据更新策略 (基于外部API)

### 更新频率
- **缓存刷新** - 每30分钟自动刷新Redis缓存
- **全量同步** - 每日凌晨2点全量同步股票数据
- **增量更新** - 检测到外部API数据变更时立即更新
- **健康检查** - 每5分钟检查外部API可用性

### 更新流程
1. **API请求** - 从外部API获取最新股票数据
2. **数据适配** - 转换外部API格式为内部格式
3. **缓存更新** - 更新多级缓存数据
4. **状态监控** - 记录更新状态和性能指标
5. **异常处理** - 处理更新过程中的异常情况

## 📊 预期效果 (基于现有API)

### 功能指标
- ✅ 支持5,448只A股股票数据获取 (基于现有API)
- ✅ 覆盖SH/SZ/BJ全市场交易所
- ✅ 利用现成数据源，无需自建采集系统
- ✅ 支持多维度筛选和代码映射功能

### 性能指标
- 🎯 缓存命中响应时间 < 50ms
- 🎯 外部API调用响应时间 < 500ms
- 🎯 并发支持能力 > 500 QPS
- 🎯 数据准确率 100% (依赖外部API)

### 可靠性指标
- 🛡️ 服务可用性 > 99.9%
- 🛡️ 外部API容错能力 < 5秒恢复
- 🛡️ 缓存降级可用性 100%

### 成本效益
- 💰 **开发成本**: 降低80% (无需自建数据采集)
- 💰 **维护成本**: 降低60% (依赖成熟外部服务)
- 💰 **时间成本**: 缩短70% (立即可用)

## 🚀 集成实施计划 (get-stockdata微服务)

### 第一阶段：基础集成 (1-2天)
1. **创建StockCodeClient模块**
   - 实现 `src/services/stock_code_client.py`
   - 封装外部API基础调用
   - 添加Redis缓存支持

2. **添加API路由**
   - 创建 `src/api/stock_code_routes.py`
   - 实现基础查询接口
   - 集成到FastAPI主应用

3. **数据模型定义**
   - 创建 `src/models/stock_models.py`
   - 定义股票基础数据结构
   - 实现数据适配器

### 第二阶段：功能完善 (1天)
1. **容错机制**
   - 添加自动重试和熔断器
   - 实现降级策略
   - 完善错误处理

2. **批量处理**
   - 创建 `src/services/batch_processor.py`
   - 实现分页获取功能
   - 支持并发处理

### 第三阶段：性能优化 (1天)
1. **缓存优化**
   - 实现多级缓存策略
   - 添加缓存预热机制
   - 优化缓存键设计

2. **监控集成**
   - 添加性能指标监控
   - 集成日志记录
   - 实现健康检查

### 与分笔数据服务集成
```python
# 在 tick_data_service.py 中集成 StockCodeClient
class TickDataService:
    def __init__(self):
        self.stock_client = StockCodeClient()  # 依赖注入

    async def get_stocks_for_tick_data(self, exchange: str = None):
        """获取需要获取分笔数据的股票列表"""
        return await self.stock_client.get_stocks_for_tick_data(exchange)
```

---

**📅 设计时间**: 2025-11-18
**👤 设计者**: AI Assistant
**🎯 服务目标**: 在get-stockdata微服务中集成股票代码客户端服务
**📍 项目路径**: `/home/bxgh/microservice-stock/services/get-stockdata/`
**🔗 外部API**: `http://124.221.80.250:8000/api/v1/stocks`
**🏗️ 部署方式**: 单一微服务，模块化设计