# 🗄️ ClickHouse数据存储和管理设计方案

## 📋 设计概述

**设计目标**: 基于已部署的ClickHouse时序数据库，设计高性能的A股分笔数据存储和管理方案

**技术选型**: ✅ **ClickHouse** - 已部署的时序数据库，专为大规模数据分析优化

**核心特性**:
- 🚀 **高性能查询** - 支持亿级数据毫秒级查询
- 📊 **时序优化** - 针对时间序列数据特殊优化
- 🗜️ **高压缩比** - 自动数据压缩，节省存储空间
- 🔄 **实时写入** - 支持高并发实时数据写入
- 📈 **分布式扩展** - 支持水平扩展集群部署

---

## 🏗️ 数据库架构设计

### ClickHouse连接配置

基于现有docker-compose配置:
```yaml
# docker-compose.infrastructure.yml
clickhouse:
  image: clickhouse/clickhouse-server:latest
  container_name: microservice-stock-clickhouse
  ports:
    - "8123:8123"  # HTTP接口
    - "9000:9000"  # TCP接口
  environment:
    - CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1
```

### 连接参数
```bash
# HTTP接口 (推荐)
HOST: localhost:8123
USER: default
PASSWORD: (空)
DATABASE: default

# TCP接口 (高性能)
HOST: localhost:9000
USER: default
DATABASE: default
```

---

## 📊 核心数据表设计

### 1. 分笔数据主表 (tick_data)

```sql
-- A股分笔数据主表
CREATE TABLE tick_data (
    -- 主键字段
    symbol String,           -- 股票代码 (000001, 600001等)
    name String,             -- 股票名称
    market String,           -- 交易所 (SH/SZ/BJ)
    trade_date Date,         -- 交易日期

    -- 时间维度
    timestamp DateTime,      -- 精确时间戳
    time_str String,         -- 时间字符串 (HH:MM:SS)

    -- 分笔数据核心字段
    price Decimal(10, 3),    -- 成交价格
    volume UInt32,           -- 成交量(手)
    amount Decimal(15, 2),   -- 成交额(元)

    -- 数据质量字段
    data_source String,      -- 数据源 (tongdaxin, akshare等)
    quality_score Float32,   -- 数据质量评分 (0-1)
    is_duplicate UInt8,      -- 是否重复记录 (0/1)

    -- 元数据字段
    created_at DateTime DEFAULT now(),  -- 创建时间
    updated_at DateTime DEFAULT now()   -- 更新时间
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(trade_date)  -- 按月分区
ORDER BY (symbol, trade_date, timestamp)  -- 排序键
SETTINGS index_granularity = 8192;
```

**设计亮点**:
- ✅ **分区策略**: 按月分区，便于数据管理和查询优化
- ✅ **排序键**: 按股票+日期+时间排序，支持快速范围查询
- ✅ **数据类型**: ClickHouse优化数据类型，提升存储和查询效率
- ✅ **质量保证**: 集成数据质量评分和重复检测字段

### 2. 股票基础信息表 (stock_info)

```sql
-- 股票基础信息表
CREATE TABLE stock_info (
    symbol String,           -- 股票代码
    name String,             -- 股票名称
    market String,           -- 交易所
    industry String,         -- 行业
    sector String,           -- 板块
    list_date Date,          -- 上市日期
    status String,           -- 状态 (active/delisted)

    -- 多格式代码映射
    tushare_code String,     -- Tushare格式代码
    akshare_code String,     -- AKShare格式代码
    wind_code String,        -- Wind格式代码
    east_money_code String,  -- 东方财富格式代码

    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY symbol;
```

### 3. 数据质量监控表 (data_quality_log)

```sql
-- 数据质量监控表
CREATE TABLE data_quality_log (
    id UInt64,               -- 自增ID
    symbol String,           -- 股票代码
    trade_date Date,         -- 交易日期
    data_source String,      -- 数据源

    -- 质量指标
    total_records UInt32,    -- 总记录数
    valid_records UInt32,    -- 有效记录数
    duplicate_records UInt32,-- 重复记录数
    quality_score Float32,   -- 质量评分

    -- 时间覆盖
    earliest_time String,    -- 最早时间
    latest_time String,      -- 最晚时间
    target_achieved UInt8,   -- 是否达到目标时间(09:25)

    -- 执行信息
    strategy_used String,    -- 使用的策略
    execution_time Float32,  -- 执行时间(秒)
    retry_count UInt8,       -- 重试次数

    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(created_at)
ORDER BY (symbol, trade_date, created_at);
```

### 4. 任务执行记录表 (task_execution_log)

```sql
-- 任务执行记录表
CREATE TABLE task_execution_log (
    task_id String,          -- 任务ID
    task_type String,        -- 任务类型 (single_stock/batch)
    status String,           -- 状态 (running/completed/failed)

    -- 任务参数
    symbols Array(String),   -- 股票代码列表
    trade_date Date,         -- 交易日期
    target_time String,      -- 目标时间

    -- 执行结果
    total_stocks UInt32,     -- 总股票数
    success_stocks UInt32,   -- 成功股票数
    failed_stocks UInt32,    -- 失败股票数

    -- 性能指标
    start_time DateTime,     -- 开始时间
    end_time DateTime,       -- 结束时间
    execution_time Float32,  -- 总执行时间

    -- 详细信息
    error_message String,    -- 错误信息
    metadata String,         -- 元数据(JSON)

    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(created_at)
ORDER BY (task_id, created_at);
```

---

## 🗜️ 数据压缩和存储优化

### ClickHouse自动压缩策略

```sql
-- 数据压缩设置
ALTER TABLE tick_data MODIFY SETTING compression = 'LZ4';
ALTER TABLE stock_info MODIFY SETTING compression = 'ZSTD';
ALTER TABLE data_quality_log MODIFY SETTING compression = 'LZ4';
ALTER TABLE task_execution_log MODIFY SETTING compression = 'LZ4';
```

### 存储优化配置

```sql
-- 优化参数设置
ALTER TABLE tick_data MODIFY SETTING
    index_granularity = 8192,
    min_index_granularity_bytes = 1048576,
    max_parts_in_total = 100000;
```

### 分区管理策略

```sql
-- 自动分区管理
-- 1. 保留最近2年的热数据
-- 2. 2-5年的数据使用压缩存储
-- 3. 5年以上数据归档或删除

-- 创建分区管理视图
CREATE MATERIALIZED VIEW partition_stats AS
SELECT
    database,
    table,
    partition,
    count() as rows,
    sum(bytes_on_disk) as bytes,
    min(min_date) as min_date,
    max(max_date) as max_date
FROM system.parts
WHERE active = 1
GROUP BY database, table, partition;
```

---

## 🔄 增量更新策略

### 1. 基于时间戳的增量更新

```python
# 增量更新逻辑设计
class IncrementalUpdateStrategy:
    def __init__(self):
        self.last_update_cache = {}

    async def get_missing_data_ranges(self, symbol: str):
        """获取缺失数据范围"""
        query = """
        SELECT
            min(trade_date) as min_date,
            max(trade_date) as max_date,
            count(distinct trade_date) as data_days
        FROM tick_data
        WHERE symbol = %(symbol)s
        """

        result = await self.clickhouse_client.execute(query, {'symbol': symbol})
        return result[0] if result else None

    async def identify_missing_dates(self, symbol: str, start_date: date, end_date: date):
        """识别缺失的交易日"""
        query = """
        SELECT distinct trade_date
        FROM tick_data
        WHERE symbol = %(symbol)s
        AND trade_date BETWEEN %(start_date)s AND %(end_date)s
        ORDER BY trade_date
        """

        existing_dates = await self.clickhouse_client.execute(query, {
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date
        })

        # 计算缺失的交易日
        trading_days = self.get_trading_days(start_date, end_date)
        existing_set = {row[0] for row in existing_dates}
        missing_dates = [day for day in trading_days if day not in existing_set]

        return missing_dates
```

### 2. 数据版本管理

```sql
-- 数据版本表
CREATE TABLE data_version (
    symbol String,
    trade_date Date,
    data_source String,
    version UInt16,          -- 数据版本号
    record_count UInt32,     -- 记录数
    checksum String,         -- 数据校验和
    created_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(version, created_at)
ORDER BY (symbol, trade_date, data_source);

-- 版本冲突检测视图
CREATE MATERIALIZED VIEW version_conflicts AS
SELECT
    symbol,
    trade_date,
    groupArray(data_source) as sources,
    count() as version_count
FROM data_version
GROUP BY symbol, trade_date
HAVING version_count > 1;
```

### 3. 智能调度策略

```python
# 智能调度逻辑
class SmartUpdateScheduler:
    def __init__(self):
        self.update_priorities = {
            'recent_data': 1,      # 最近1天 - 最高优先级
            'missing_data': 2,     # 缺失数据 - 高优先级
            'quality_check': 3,    # 质量检查 - 中等优先级
            'historical_data': 4   # 历史数据 - 低优先级
        }

    async def schedule_updates(self):
        """智能调度更新任务"""
        # 1. 检查最近交易日数据
        recent_missing = await self.check_recent_data()

        # 2. 识别历史缺失数据
        historical_missing = await self.check_historical_gaps()

        # 3. 质量检查需要重新处理的数据
        quality_issues = await self.check_quality_issues()

        # 4. 生成调度任务
        tasks = []
        tasks.extend(self.create_tasks(recent_missing, priority=1))
        tasks.extend(self.create_tasks(historical_missing, priority=2))
        tasks.extend(self.create_tasks(quality_issues, priority=3))

        return sorted(tasks, key=lambda x: x.priority)
```

---

## 📈 查询性能优化

### 1. 索引策略

```sql
-- 为常用查询创建物化视图
CREATE MATERIALIZED VIEW tick_data_daily_summary AS
SELECT
    symbol,
    trade_date,
    count() as tick_count,
    min(price) as min_price,
    max(price) as max_price,
    sum(volume) as total_volume,
    sum(amount) as total_amount,
    first_value(price) as open_price,
    last_value(price) as close_price
FROM tick_data
GROUP BY symbol, trade_date;

CREATE MATERIALIZED VIEW tick_data_intraday_stats AS
SELECT
    symbol,
    trade_date,
    toHour(timestamp) as hour,
    count() as tick_count,
    avg(price) as avg_price,
    sum(volume) as volume
FROM tick_data
GROUP BY symbol, trade_date, hour;
```

### 2. 查询优化配置

```sql
-- 查询优化设置
SET max_threads = 8;
SET max_memory_usage = 10000000000;  -- 10GB
SET max_result_rows = 1000000;
SET max_result_bytes = 1000000000;   -- 1GB

-- 启用查询缓存
SET use_uncompressed_cache = 1;
SET compress_ongoing_data = 1;
```

### 3. 分区裁剪优化

```python
# 分区裁剪查询
def optimized_query(symbol: str, start_date: date, end_date: date):
    """利用分区裁剪的优化查询"""
    query = """
    SELECT *
    FROM tick_data
    WHERE symbol = %(symbol)s
    AND trade_date BETWEEN %(start_date)s AND %(end_date)s
    AND timestamp >= %(start_datetime)s
    AND timestamp <= %(end_datetime)s
    ORDER BY timestamp
    """

    return query
```

---

## 🔧 数据访问层设计

### 1. ClickHouse客户端封装

```python
# clickhouse_client.py
import asyncio
from clickhouse_driver import Client as ClickHouseClient
from clickhouse_driver.async_ import Client as AsyncClickHouseClient

class ClickHouseService:
    def __init__(self, host='localhost', port=9000, user='default',
                 password='', database='default'):
        self.client = AsyncClickHouseClient(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            settings={'max_execution_time': 60}
        )

    async def execute(self, query: str, params: dict = None):
        """执行查询"""
        try:
            result = await self.client.execute(query, params, with_column_types=True)
            return result
        except Exception as e:
            logger.error(f"ClickHouse查询失败: {e}")
            raise

    async def insert_tick_data(self, tick_data_list: List[TickData]):
        """批量插入分笔数据"""
        query = """
        INSERT INTO tick_data (
            symbol, name, market, trade_date, timestamp, time_str,
            price, volume, amount, data_source, quality_score, is_duplicate
        ) VALUES
        """

        data = [
            (
                tick.symbol, tick.name, tick.market, tick.trade_date,
                tick.timestamp, tick.time_str, tick.price, tick.volume,
                tick.amount, tick.data_source, tick.quality_score, tick.is_duplicate
            )
            for tick in tick_data_list
        ]

        await self.execute(query, data)

    async def query_tick_data(self, symbol: str, start_date: date, end_date: date):
        """查询分笔数据"""
        query = """
        SELECT *
        FROM tick_data
        WHERE symbol = %(symbol)s
        AND trade_date BETWEEN %(start_date)s AND %(end_date)s
        ORDER BY timestamp
        """

        return await self.execute(query, {
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date
        })
```

### 2. 数据缓存策略

```python
# cache_manager.py
class TickDataCache:
    def __init__(self, redis_client, clickhouse_service):
        self.redis = redis_client
        self.clickhouse = clickhouse_service
        self.cache_ttl = 3600  # 1小时

    async def get_cached_data(self, symbol: str, date: date):
        """获取缓存数据"""
        cache_key = f"tick_data:{symbol}:{date}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return json.loads(cached_data)
        return None

    async def cache_data(self, symbol: str, date: date, data: List[dict]):
        """缓存数据"""
        cache_key = f"tick_data:{symbol}:{date}"
        await self.redis.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(data, default=str)
        )

    async def get_or_load_data(self, symbol: str, date: date):
        """获取或加载数据"""
        # 1. 尝试从缓存获取
        cached_data = await self.get_cached_data(symbol, date)
        if cached_data:
            return cached_data

        # 2. 从ClickHouse加载
        data = await self.clickhouse.query_tick_data(symbol, date, date)

        # 3. 缓存结果
        if data:
            await self.cache_data(symbol, date, data)

        return data
```

---

## 📊 数据质量监控

### 1. 实时质量监控

```sql
-- 数据质量监控视图
CREATE MATERIALIZED VIEW data_quality_monitor AS
SELECT
    symbol,
    trade_date,
    count() as total_records,
    sumIf(1, quality_score >= 0.9) as high_quality_records,
    sumIf(1, quality_score >= 0.8 AND quality_score < 0.9) as medium_quality_records,
    sumIf(1, quality_score < 0.8) as low_quality_records,
    avg(quality_score) as avg_quality_score,
    min(timestamp) as earliest_time,
    max(timestamp) as latest_time
FROM tick_data
WHERE trade_date >= today() - INTERVAL 7 DAY
GROUP BY symbol, trade_date;
```

### 2. 异常检测

```python
# anomaly_detection.py
class DataAnomalyDetector:
    def __init__(self, clickhouse_service):
        self.clickhouse = clickhouse_service

    async def detect_price_anomalies(self, symbol: str, date: date):
        """检测价格异常"""
        query = """
        SELECT
            timestamp,
            price,
            lag(price) OVER (ORDER BY timestamp) as prev_price,
            (price - lag(price) OVER (ORDER BY timestamp)) / lag(price) OVER (ORDER BY timestamp) as price_change
        FROM tick_data
        WHERE symbol = %(symbol)s AND trade_date = %(date)s
        HAVING abs(price_change) > 0.1  -- 价格变动超过10%
        ORDER BY timestamp
        """

        return await self.clickhouse.execute(query, {
            'symbol': symbol,
            'date': date
        })

    async def detect_volume_anomalies(self, symbol: str, date: date):
        """检测成交量异常"""
        query = """
        SELECT
            timestamp,
            volume,
            avg(volume) OVER (
                ORDER BY timestamp
                ROWS BETWEEN 10 PRECEDING AND 10 FOLLOWING
            ) as avg_volume,
            volume / avg(volume) as volume_ratio
        FROM tick_data
        WHERE symbol = %(symbol)s AND trade_date = %(date)s
        HAVING volume_ratio > 5 OR volume_ratio < 0.2
        ORDER BY timestamp
        """

        return await self.clickhouse.execute(query, {
            'symbol': symbol,
            'date': date
        })
```

---

## 🚀 部署和运维

### 1. 数据库初始化脚本

```sql
-- init_clickhouse.sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS stock_data;

-- 创建数据表
USE stock_data;

-- 执行上述所有CREATE TABLE语句

-- 创建用户和权限
CREATE USER IF NOT EXISTS stock_user
IDENTIFIED BY 'stock_password'
GRANT SELECT, INSERT, UPDATE, DELETE ON stock_data.* TO stock_user;

-- 创建角色
CREATE ROLE IF NOT EXISTS stock_reader;
CREATE ROLE IF NOT EXISTS stock_writer;

GRANT SELECT ON stock_data.* TO stock_reader;
GRANT SELECT, INSERT, UPDATE ON stock_data.* TO stock_writer;

GRANT stock_reader TO stock_user;
GRANT stock_writer TO stock_user;
```

### 2. 监控指标

```sql
-- 性能监控查询
SELECT
    database,
    table,
    sum(rows) as total_rows,
    sum(bytes_on_disk) as total_bytes,
    sum(bytes_on_disk) / sum(rows) as avg_row_size
FROM system.parts
WHERE active = 1
GROUP BY database, table;

-- 查询性能监控
SELECT
    query,
    read_rows,
    read_bytes,
    elapsed_seconds,
    memory_usage
FROM system.query_log
WHERE event_date = today()
ORDER BY elapsed_seconds DESC
LIMIT 10;
```

### 3. 备份策略

```bash
# 备份脚本
#!/bin/bash
# backup_clickhouse.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/clickhouse"
DB_NAME="stock_data"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 导出数据
clickhouse-client -q "
    SELECT * FROM $DB_NAME.tick_data
    WHERE trade_date BETWEEN '2020-01-01' AND '$DATE'
    FORMAT CSV
" > $BACKUP_DIR/tick_data_$DATE.csv

# 压缩备份
gzip $BACKUP_DIR/tick_data_$DATE.csv

# 清理旧备份 (保留30天)
find $BACKUP_DIR -name "*.csv.gz" -mtime +30 -delete
```

---

## 📋 实施计划

### 阶段一: 基础设施 (1周)
- [ ] ClickHouse数据库初始化
- [ ] 创建核心数据表
- [ ] 配置用户权限
- [ ] 建立连接池

### 阶段二: 数据集成 (1周)
- [ ] 实现ClickHouse服务客户端
- [ ] 集成数据写入逻辑
- [ ] 实现批量插入优化
- [ ] 添加事务处理

### 阶段三: 查询优化 (1周)
- [ ] 创建物化视图
- [ ] 优化查询索引
- [ ] 实现缓存策略
- [ ] 性能基准测试

### 阶段四: 监控运维 (1周)
- [ ] 数据质量监控
- [ ] 异常检测系统
- [ ] 备份恢复策略
- [ ] 性能监控仪表板

---

## 🎯 预期效果

### 存储性能
- ✅ **写入性能**: 10万条/秒 (批量写入)
- ✅ **查询性能**: 毫秒级响应 (亿级数据)
- ✅ **压缩比**: 10:1 (相比原始数据)
- ✅ **存储成本**: 降低70% (高压缩比)

### 查询能力
- ✅ **时间范围查询**: 毫秒级响应
- ✅ **聚合查询**: 秒级响应
- ✅ **实时分析**: 支持实时仪表板
- ✅ **历史回测**: 支持多年数据回测

### 运维便利
- ✅ **自动分区**: 无需手动管理
- ✅ **自动压缩**: 节省存储空间
- ✅ **实时监控**: 完整监控体系
- ✅ **高可用**: 支持集群部署

---

**设计状态**: ✅ **完整设计方案**
**技术可行性**: ✅ **基于现有ClickHouse部署**
**实施复杂度**: 🟡 **中等** (需要分阶段实施)
**预期收益**: 🚀 **高性能数据存储和分析能力**