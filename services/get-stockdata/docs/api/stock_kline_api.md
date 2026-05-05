# 股票 K 线数据 API 接口文档

## 概述
本文档详细说明了 `get-stockdata` 微服务中历史 K 线（蜡烛图）数据的相关接口。系统采用双层存储策略以平衡性能与可靠性：
- **主存储**: 本地 ClickHouse，用于高性能数据检索。
- **备份存储**: 腾讯云 MySQL，提供数据持久化保障。

## 数据检索策略
为了确保高可用性和低延迟，服务对 K 线数据实施了多层路由策略：

1. **ClickHouse 层 (主选)**: 服务首先尝试从本地 ClickHouse 实例获取数据，该层针对高性能分析查询进行了优化。
2. **MySQL 层 (降级)**: 如果 ClickHouse 中未找到数据或实例不可用，服务将自动切换到远程腾讯云 MySQL 数据库。
3. **透明故障转移**: 故障转移过程对 API 使用者是透明的，但响应中的 `source` 字段会注明数据来源。

## 1. 数据查询接口

### 1.1 获取历史 K 线
返回指定股票的历史日线 K 线数据。

- **URL**: `/api/v1/quotes/history/{stock_code}`
- **Method**: `GET`
- **路径参数**:
  - `stock_code`: 6 位股票代码 (例如 `600519`)
- **查询参数**:
  - `start_date`: 开始日期 (`YYYY-MM-DD`, 默认 30 天前)
  - `end_date`: 结束日期 (`YYYY-MM-DD`, 默认当天)
  - `frequency`: 数据频率 (`d`=日线, `w`=周线, `m`=月线)。*注意：目前仅支持 `d`。*
  - `adjust`: 复权方式 (`0`=不复权, `1`=前复权, `2`=后复权, 默认 `2`)
- **全地址示例**:
  - **内网 API**: `http://get-stockdata:8083/api/v1/quotes/history/600519?start_date=2025-12-01&end_date=2025-12-29&adjust=2`
  - **本地开发访问**: `http://localhost:8083/api/v1/quotes/history/600519?start_date=2025-01-01`
  > [!NOTE]
  > 在开发环境中，`get-stockdata` 容器使用 `host` 网络模式，因此直接通过 `8083` 端口访问。
- **响应示例**:
  ```json
  {
    "success": true,
    "code": "600519",
    "frequency": "d",
    "data": [
      {
        "trade_date": "2023-12-01",
        "open": 1700.0,
        "high": 1720.0,
        "low": 1690.0,
        "close": 1710.0,
        "volume": 12345,
        "amount": 21110000.0,
        ...
      }
    ],
    "count": 1,
    "source": "ClickHouse (Local)"
  }
  ```

---

## 2. 数据同步接口

### 2.1 触发 K 线同步
启动后台任务，将远程数据源的 K 线数据同步到本地仓库。

### 2.2 触发复权因子同步
将腾讯云 MySQL 中的 `stock_adjust_factor` 表同步到本地 ClickHouse。此数据用于支持 K 线的前/后复权。

- **Docker CLI 方式**:
  ```bash
  docker exec -it get-stockdata-api-dev python scripts/sync_factors_to_clickhouse.py
  ```

### 2.1 Docker CLI 方式
除了通过 API，也可以在宿主机直接使用 Docker 命令触发同步脚本：

- **智能增量同步 (推荐)**:
  ```bash
  docker exec -it get-stockdata-api-dev python scripts/sync_kline_to_clickhouse.py --mode smart
  ```
- **根据创建时间同步 (用于每日维护)**:
  ```bash
  docker exec -it get-stockdata-api-dev python scripts/sync_kline_to_clickhouse.py --mode created_at --hours 48
  ```
- **全量同步 (初始化使用)**:
  ```bash
  docker exec -it get-stockdata-api-dev python scripts/sync_kline_to_clickhouse.py --mode full --batch-size 10000
  ```

### 2.2 HTTP API 方式
**URL**: `/api/v1/sync/kline`
**Method**: `POST`
**请求体**:
  ```json
  {
    "mode": "smart",        // full, incremental, smart, created_at
    "days": 7,              // 用于 incremental 模式
    "hours": 48,            // 用于 created_at 模式
    "batch_size": 10000,    // 每批次记录数
    "sync_factors": true    // 是否同步复权因子 (K线同步完成后串行执行)
  }
  ```
- **参数说明**:
  - `full`: 全量同步所有历史数据。
  - `smart`: 智能增量同步，仅同步 ClickHouse 中最新日期之后的数据。
  - `created_at`: 根据数据源中的 `created_at` 时间戳进行增量同步。
  - `sync_factors`: 建议开启，确保复权行情计算所需的因子同步更新。
- **响应示例**:
  ```json
  {
    "status": "accepted",
    "message": "Synchronization task started in background",
    "check_status_url": "/api/v1/sync/kline/status"
  }
  ```

---

## 3. 监控接口

### 3.1 获取同步状态
查询当前后台同步任务的运行状态。

- **URL**: `/api/v1/sync/kline/status`
- **Method**: `GET`
- **响应示例**:
  ```json
  {
    "status": "running",
    "progress": "45%",
    "last_update": "2025-12-29T15:00:00"
  }
  ```

### 3.2 获取同步历史
返回最近执行的同步任务及其结果。

- **URL**: `/api/v1/sync/kline/history`
- **Method**: `GET`
- **查询参数**:
  - `limit`: 返回记录的数量 (默认 7)

---

## 4. 内部数据透传 (云端数据源)

### 4.1 获取原始历史数据 (Baostock 代理)
直接调用云端服务器上的 Baostock 库获取 K 线数据。

- **实际应用**:
  - **K线同步主供**: 该代理是本地 K 线仓库最完整、最准确的原始数据来源。
  - **高精度验证**: 当本地 ClickHouse 数据存疑时，可直接调用此接口进行比对。
- **基础 URL**: `http://124.221.80.250:8001`
- **URL**: `/api/v1/history/kline/{code}`
- **全地址示例**: `http://124.221.80.250:8001/api/v1/history/kline/600519?start_date=2025-12-01&end_date=2025-12-30&adjust=1`
- **Method**: `GET`
- **参数**:
  - `start_date`: `YYYY-MM-DD` (例如 `2025-12-01`)
  - `end_date`: `YYYY-MM-DD`
  - `adjust`: 复权方式 (`1`=后复权, `2`=前复权, `3`=不复权)
  - `frequency`: `d`=日线, `w`=周线, `m`=月线, `5`=5分钟线

> [!NOTE]
> 之前的文档中误将 AkShare 代理 (`8003`) 列为 K 线来源。经核查，AkShare 代理主要负责 **财务、估值、行业和实时人气榜单** 数据，而 **历史 K 线** 的原始查询请统一使用 Baostock 代理 (`8001`)。

---

---

## 5. 数据规格 (Data Specification)

### 5.1 复权因子 (Adjustment Factors)
复权因子存储在本地 ClickHouse 的 `stock_adjust_factor` 表中，通过 `(stock_code, ex_date)` 唯一标识。

- **表结构**:
  | 字段名 | 类型 | 说明 |
  | :--- | :--- | :--- |
  | `stock_code` | `String` | 股票代码 |
  | `ex_date` | `Date` | 除权日期 |
  | `fore_factor` | `Decimal` | 前复权因子 |
  | `back_factor` | `Decimal` | 后复权因子 |
  | `update_time` | `DateTime` | 最后更新时间 |

- **用途**: 
  - **后复权价格** = 原始价格 * 该日期的 `back_factor`
  - **前复权价格** = 原始价格 * 该日期的 `fore_factor`

---

## 数据规范
- **股票代码**: 统一为 6 位数字字符串 (`zfill(6)`)。
- **时区**: 中国标准时间 (`Asia/Shanghai`)。
- **日期格式**: 公共接口使用 `YYYY-MM-DD`，AkShare 代理使用 `YYYYMMDD`。
- **空值处理**: 数据源中的 `NaN` 或 `Inf` 会序列化为 JSON 的 `null`。
