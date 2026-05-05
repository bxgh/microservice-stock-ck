# Story 1.1: 策略服务脚手架与配置

## 目标
初始化 `quant-strategy` 服务结构，完成数据库连接、日志、异常处理等基础设施配置，为后续策略开发提供标准化环境。

## 详细开发内容规范

### 1. 项目结构
- 使用 FastAPI 作为主框架，目录结构建议如下：
  ```
  quant-strategy/
    ├── src/
    │   ├── main.py
    │   ├── api/
    │   ├── core/
    │   ├── models/
    │   ├── services/
    │   ├── utils/
    │   └── config.py
    ├── tests/
    ├── requirements.txt
    └── README.md
  ```

### 2. 配置管理
- 所有配置（数据库、Nacos、日志等）集中在 `config.py`，支持环境变量覆盖。
- 配置项包括：
  - ClickHouse 连接参数（host, port, user, password, database）
  - Redis 连接参数（host, port, db, password）
  - Nacos 注册与发现参数（server, namespace, group, service_name）
  - 日志级别、格式、输出路径

### 3. 数据库连接池
- 使用 `clickhouse-driver` 或 `sqlalchemy` 连接 ClickHouse，初始化连接池。
- 使用 `redis-py` 创建 Redis 连接池，支持多线程/异步访问。

### 4. Nacos 服务注册与发现
- 集成 `nacos-sdk-python`，实现服务注册、健康检查、配置拉取。
- 启动时自动注册服务，异常时自动注销。

### 5. 日志系统
- 采用 `loguru` 或 `logging`，统一日志格式（建议 JSON），包含时间、级别、服务名、trace_id。
- 日志分级输出（info、warning、error），支持文件和控制台双输出。

### 6. 异常处理
- 全局异常捕获，返回标准化错误响应（包含错误码、信息、trace_id）。
- 关键操作（数据库、缓存、外部服务）均需异常保护，日志记录详细错误信息。

### 7. 代码规范与文档
- 遵循 PEP8 代码规范，关键模块需补充 docstring。
- 项目根目录提供开发文档（README.md），说明环境依赖、启动方式、配置项说明。

### 8. 单元测试
- 对配置加载、数据库连接、Nacos注册、日志输出等核心功能编写单元测试，覆盖率不低于80%。

### 9. MySQL 数据库连接池
- 在 `config.py` 中新增 MySQL 配置项，示例：
  ```python
  DB_CONFIG = {
      'host': 'sh-cdb-h7flpxu4.sql.tencentcdb.com',
      'port': 26300,
      'database': 'alwaysup',
      'user': 'root',
      'password': 'alwaysup@888',
      'charset': 'utf8mb4'
  }
  ```
- 推荐使用 `aiomysql`（异步）或 `sqlalchemy`（同步/异步）实现连接池管理。
- 连接池需支持自动重连、超时设置、最大连接数限制。
- 所有数据库操作需封装在统一的数据访问层，异常需统一处理并记录日志。
- 单元测试需覆盖 MySQL 连接初始化、基本 CRUD 操作、异常场景。
