# Story 10.1: ClickHouse 表结构设计

## Story 信息

| 字段 | 值 |
|------|-----|
| **Story ID** | 10.1 |
| **所属 Epic** | EPIC-010 本地数据仓库 |
| **优先级** | P0 |
| **预估工时** | 2 天 |
| **前置依赖** | Story 10.0 |

---

## 目标

在 ClickHouse 中创建核心数据表，为数据采集和查询提供存储基础。

---

## 验收标准

1. ✅ 日K线表 `kline_daily` 创建成功
2. ✅ 财务数据表 `financials` 创建成功
3. ✅ 估值历史表 `valuation_history` 创建成功
4. ✅ 因子值表 `factor_values` 创建成功
5. ✅ 分区和 TTL 策略配置正确

---

## 任务分解

### Task 1: 创建数据库

```sql
CREATE DATABASE IF NOT EXISTS stock_data;
```

### Task 2: 日K线表

```sql
CREATE TABLE IF NOT EXISTS stock_data.kline_daily (
    stock_code String,
    trade_date Date,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64,
    amount Float64,
    turnover_rate Float32,
    adj_factor Float64,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, trade_date)
SETTINGS index_granularity = 8192;
```

### Task 3: 财务数据表

```sql
CREATE TABLE IF NOT EXISTS stock_data.financials (
    stock_code String,
    report_date Date,
    report_type String,
    revenue Float64,
    net_profit Float64,
    eps Float64,
    roe Float32,
    gross_margin Float32,
    operating_cash_flow Float64,
    total_assets Float64,
    total_liabilities Float64,
    created_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(created_at)
PARTITION BY toYear(report_date)
ORDER BY (stock_code, report_date);
```

### Task 4: 估值历史表

```sql
CREATE TABLE IF NOT EXISTS stock_data.valuation_history (
    stock_code String,
    trade_date Date,
    pe_ttm Float32,
    pb Float32,
    ps_ttm Float32,
    pcf_ttm Float32,
    total_mv Float64,
    circ_mv Float64,
    dividend_yield Float32
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, trade_date)
TTL trade_date + INTERVAL 5 YEAR;
```

### Task 5: 因子值表

```sql
CREATE TABLE IF NOT EXISTS stock_data.factor_values (
    factor_id String,
    stock_code String,
    compute_date Date,
    value Float64,
    rank UInt16
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(compute_date)
ORDER BY (factor_id, stock_code, compute_date)
TTL compute_date + INTERVAL 1 YEAR;
```

### Task 6: 初始化脚本

创建 `scripts/init_clickhouse.sql` 统一管理建表语句。

---

## 验证方法

```bash
# 进入 ClickHouse 容器
docker exec -it microservice-stock-clickhouse clickhouse-client

# 检查表是否创建
SHOW TABLES FROM stock_data;
```

---

*创建日期: 2025-12-23*
