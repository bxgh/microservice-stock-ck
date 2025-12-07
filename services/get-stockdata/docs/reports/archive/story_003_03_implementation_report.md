# Story 003-03 实施报告：ClickHouse Writer 实现

**Story ID**: STORY-003-03  
**实施日期**: 2025-12-01  
**状态**: ✅ 已完成  

---

## 📋 实施概述

成功实现了 ClickHouseWriter，支持将盘口快照数据（五档行情）批量写入 ClickHouse 数据库。完成了从依赖安装、表结构创建到测试验证的完整流程。

## 🎯 验收标准完成情况

### 功能验收 ✅

- [x] **添加 clickhouse-driver 依赖** - 已添加到 `requirements.txt`
- [x] **创建表结构** - 36字段盘口快照表
- [x] **实现 ClickHouseWriter 类** - 支持批量写入、缓冲管理
- [x] **实现异步提交机制** - 缓冲区达到批次大小自动提交
- [x] **实现错误处理** - ClickHouseError 捕获和日志记录
- [x] **测试验证** - **5/5 测试通过** ✅

---

## 📊 测试结果

### 测试执行

```bash
============ test session starts ============
tests/test_clickhouse_writer.py::TestClickHouseWriter::test_connection PASSED [ 20%]
tests/test_clickhouse_writer.py::TestClickHouseWriter::test_write_single_snapshot PASSED [ 40%]
tests/test_clickhouse_writer.py::TestClickHouseWriter::test_batch_write PASSED [ 60%]
tests/test_clickhouse_writer.py::TestClickHouseWriter::test_buffer_auto_flush PASSED [ 80%]
tests/test_clickhouse_writer.py::TestClickHouseWriter::test_get_stats PASSED [100%]

============ 5 passed in 0.75s ============
```

### 数据验证

查询写入的数据：
```sql
SELECT count(), stock_code, stock_name 
FROM stock_data.snapshot_data 
GROUP BY stock_code, stock_name;
```

结果：
- 100 条 "浦发银行" 记录 ✅
- 多条测试数据记录 ✅
- 五档数据完整 ✅

验证样本数据：
```
snapshot_time: 2025-12-01 14:43:43.302
stock_code: 000001
current_price: 12.5
bid_price1: 12.49, bid_volume1: 100
ask_price1: 12.50, ask_volume1: 120
```

---

## 💻 实现细节

### 1. 表结构设计

根据项目文档回顾，发现实际需求是 **盘口快照** 而非传统分笔数据。

```sql
CREATE TABLE snapshot_data (
    -- 时间（2字段）
    snapshot_time DateTime64(3),  -- 毫秒精度
    trade_date Date,
    
    -- 股票信息（3字段）
    stock_code String,
    stock_name String,
    market String,
    
    -- 当前行情（5字段）
    current_price, open_price, high_price, low_price, pre_close
    
    -- 买五档（10字段）
    bid_price1-5, bid_volume1-5
    
    -- 卖五档（10字段）
    ask_price1-5, ask_volume1-5
    
    -- 成交统计（3字段）
    total_volume, total_amount, turnover_rate
    
    -- 元数据（3字段）
    data_source, pool_level, created_at (DEFAULT now())
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(trade_date)  -- 按月分区
ORDER BY (stock_code, snapshot_time)  -- 时间序列优化
TTL trade_date + INTERVAL 90 DAY;  -- 90天热数据
```

**设计亮点**：
- **36个字段** 覆盖完整五档盘口
- **毫秒时间戳** 支持高频数据（DateTime64(3)）
- **按月分区** 便于数据管理和查询优化
- **TTL 90天** 自动清理历史数据，节省存储
- **排序键优化** 按股票+时间排序，加速时间序列分析

### 2. ClickHouseWriter 实现

```python
class ClickHouseWriter:
    def __init__(self, host, port, database, batch_size=5000):
        self.client = Client(host, port, database)
        self._buffer = []
        self.batch_size = batch_size
    
    def write_snapshot(self, snapshot: SnapshotData):
        self._buffer.append(snapshot)
        if len(self._buffer) >= self.batch_size:
            self.flush()
    
    def flush(self):
        data = [self._to_row(s) for s in self._buffer]
        self.client.execute(
            '''INSERT INTO snapshot_data (
                snapshot_time, trade_date, stock_code, ...
            ) VALUES''',
            data
        )
        self._buffer.clear()
```

**关键特性**：
- **批量缓冲** - 默认 5000 条/批，显著提升性能
- **自动提交** - 缓冲区满时自动 flush
- **错误处理** - ClickHouseError 异常捕获
- **统计接口** - `get_stats()` 返回缓冲区状态

### 3. 数据模型

创建了 `SnapshotData` 类，简化数据构建：

```python
snapshot = SnapshotData(
    snapshot_time=datetime.now(),
    stock_code='000001',
    stock_name='平安银行',
    current_price=12.50,
    bid_price1=12.49, bid_volume1=100,
    ask_price1=12.50, ask_volume1=120,
    total_volume=1000000,
    pool_level='L1'
)

writer.write_snapshot(snapshot)
```

---

## 🐛 问题解决记录

### 问题 1: Docker 网络无法连接

**错误**: 
```
clickhouse_driver.errors.NetworkError: Code: 210. 
Temporary failure in name resolution (microservice-stock-clickhouse:9000)
```

**原因**: `docker-compose.dev.yml` 配置的网络名称与 ClickHouse 实际所在网络不一致。

**诊断过程**:
1. 检查 ClickHouse 容器：`docker ps` 显示网络为 `microservice-stock_microservice-stock`
2. 检查测试容器：试图连接 `microservice-stock` 网络
3. 发现不匹配

**解决方案**:
```yaml
# docker-compose.dev.yml
networks:
  microservice-stock:
    external: true
    name: microservice-stock_microservice-stock  # 明确指定网络名
```

### 问题 2: 列数不匹配

**错误**:
```
ValueError: Expected 36 columns, got 35
```

**原因**: 表有 `created_at` 字段（DEFAULT now()），使用 `INSERT INTO table VALUES` 时，ClickHouse 期望所有 36 列，但我们只提供了 35 列。

**解决方案**: 修改 INSERT 语句，明确指定列名（不包含 `created_at`）：

```python
self.client.execute(
    '''INSERT INTO snapshot_data (
        snapshot_time, trade_date, stock_code, stock_name, market,
        current_price, open_price, high_price, low_price, pre_close,
        bid_price1, bid_volume1, bid_price2, bid_volume2, ...
        data_source, pool_level
    ) VALUES''',
    data
)
```

### 问题 3: Docker 镜像依赖未安装

**问题**: 在容器中运行测试时，`clickhouse-driver` 模块未安装。

**原因**: 依赖是在用户空间安装的（`pip install --user`），容器重启后丢失。

**解决方案**:
1. 更新 `requirements.txt` 添加 `clickhouse-driver>=0.2.6`
2. 重新构建 Docker 镜像：
   ```bash
   docker compose -f docker-compose.dev.yml build get-stockdata
   ```

---

## 📁 交付文件

### 代码文件

1. **`src/storage/clickhouse_writer.py`** - Writer 实现
   - `SnapshotData` 数据模型类
   - `ClickHouseWriter` 写入器类
   - 批量写入、缓冲管理、错误处理

2. **`scripts/init_clickhouse.sql`** - 表结构 SQL
   - `snapshot_data` 表定义
   - `snapshot_daily_stats` 物化视图
   - 索引和权限配置

3. **`scripts/run_init_clickhouse.py`** - 初始化脚本
   - 读取 SQL 文件
   - 执行建表语句
   - 错误处理和日志

### 测试文件

4. **`tests/test_clickhouse_writer.py`** - 功能测试
   - `test_connection` - 连接测试
   - `test_write_single_snapshot` - 单条写入
   - `test_batch_write` - 批量写入
   - `test_buffer_auto_flush` - 自动提交
   - `test_get_stats` - 统计信息

### 配置文件

5. **`requirements.txt`** - 新增依赖
   ```
   clickhouse-driver>=0.2.6  # ClickHouse数据库驱动
   ```

6. **`docker-compose.dev.yml`** - 网络配置修复
   ```yaml
   networks:
     microservice-stock:
       external: true
       name: microservice-stock_microservice-stock
   ```

---

## 🚀 性能特性

- **批量写入**: 默认 5000 条/批，可配置
- **自动提交**: 缓冲区满时自动 flush
- **错误处理**: 完善的异常捕获和日志
- **连接管理**: 自动初始化和断开
- **查询接口**: 支持执行任意 SQL 查询

---

## 🎓 经验总结

### Docker 网络

1. **网络命名规则**: Docker Compose 创建的网络名称是 `<project>_<network>`
2. **诊断方法**: 使用 `docker ps` 和 `docker network ls` 检查实际网络
3. **配置方法**: 使用 `name` 属性明确指定外部网络

### ClickHouse INSERT

1. **列名显式指定**: 当表有 DEFAULT 字段时，明确指定列名避免列数不匹配
2. **批量性能**: 批量 INSERT 比单条快 10-100 倍
3. **数据类型匹配**: Python 的 `datetime` 自动转换为 ClickHouse 的 `DateTime64`

### 测试策略

1. **逐步调试**: 先解决网络问题，再解决数据格式问题
2. **数据验证**: 测试后查询数据库验证实际写入结果
3. **隔离环境**: 使用 Docker 确保测试环境一致性

---

## 🔄 与原设计文档的差异

### 发现的关键问题

原设计文档 (`clickhouse-data-storage-design.md`) 定义的是简化的 `tick_data` 表，仅包含：
- `time, price, volume, amount, direction`

但通过文档回顾发现：
- 项目实际采集的是 **Mootdx `quotes()` 接口**
- 返回数据包含 **五档盘口** (Bid1-5, Ask1-5)
- 数据规模是 **46 列**（快照）而非 5 列（分笔）

### 调整方案

创建了 `snapshot_data` 表替代 `tick_data`，更符合实际需求：
- 36 个数据字段（时间、股票、行情、五档、成交、元数据）
- 支持 L1/L2/L3 股票池级别标识
- 数据源标识（mootdx/tongdaxin等）

---

## 🚀 下一步

1. **集成到采集流程** - 将 ClickHouseWriter 集成到 SnapshotRecorder
2. **性能基准测试** - 验证 10万行/秒写入性能
3. **监控仪表板** - 使用 Grafana 可视化快照数据
4. **Parquet 归档优化** - 完成 Story 4

---

**实施人员**: Antigravity AI  
**文档版本**: v1.0  
**完成时间**: 2025-12-01
