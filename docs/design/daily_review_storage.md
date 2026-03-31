# 每日复盘数据存储设计 (Daily Review Storage Specification) - V3 (极简单机版)

本文件定义了“每日复盘”模块在 ClickHouse 中的存储设计。基于**实事求是**与**防御过度设计**的工程原则，由于该模块数据量极小（约 250 行/年），系统**不采用**分布式分片架构，而是将数据统一持久化于主控节点 (Node 41)。

## 1. 核心表结构 (Node 41 独占)

以下表仅在 Node 41 节点上创建，不进行跨节点分片。

### 1.1 市场整体汇总表 (market_review_daily_summary)
```sql
CREATE TABLE IF NOT EXISTS stock_data.market_review_daily_summary (
    trade_date Date,
    hs300_chg Float64, zz500_chg Float64, zz1000_chg Float64, bz50_chg Float64,
    up_count UInt32, down_count UInt32,
    limit_up_count UInt32, limit_down_count UInt32,
    market_amount Decimal(20, 2), amount_z_score Float64,
    money_making_idx Float64,
    updated_at DateTime DEFAULT now()
) ENGINE = MergeTree() ORDER BY trade_date;
```

### 1.2 汇金特征表 (market_review_huijin)
```sql
CREATE TABLE IF NOT EXISTS stock_data.market_review_huijin (
    trade_date Date,
    intensity Float64 COMMENT '护盘强度(0-100)',
    etf_z_scores Map(String, Float64),
    avg_premium Float64,
    updated_at DateTime DEFAULT now()
) ENGINE = MergeTree() ORDER BY trade_date;
```

> **字段聚合规则 (intensity)**：
> `intensity` (0-100) 的标量值由盘中实时的汇金方程式 $I_{admin}(t)$ 降维而来。当前版本的聚合规则定义为：取当日**尾盘 30 分钟（14:30-15:00）** 内 `(即时成交量 Z-Score × IOPV 绝对溢价率)` 触发乘积的**时间积分均值**，并缩放至 0-100 区间。无触发时记为 0。


### 1.3 机构资金表 (market_review_institution)
```sql
CREATE TABLE IF NOT EXISTS stock_data.market_review_institution (
    trade_date Date,
    net_amount Decimal(20, 2),
    north_funds_net Decimal(20, 2),
    active_stock_count UInt32,
    top_sectors Array(String),
    updated_at DateTime DEFAULT now()
) ENGINE = MergeTree() ORDER BY trade_date;
```

### 1.4 游资热点表 (market_review_yousi)
```sql
CREATE TABLE IF NOT EXISTS stock_data.market_review_yousi (
    trade_date Date,
    limit_success_rate Float64,
    limit_stairs Map(String, UInt32),
    top_concepts Array(String),
    updated_at DateTime DEFAULT now()
) ENGINE = MergeTree() ORDER BY trade_date;
```

### 1.5 量化行为表 (market_review_quant)
```sql
CREATE TABLE IF NOT EXISTS stock_data.market_review_quant (
    trade_date Date,
    small_order_ratio Float64,
    t0_sell_pressure Float64,
    updated_at DateTime DEFAULT now()
) ENGINE = MergeTree() ORDER BY trade_date;
```

## 2. 系统视图与查询

为了保持与前端逻辑的兼容，提供一个单机联合视图：

```sql
CREATE VIEW IF NOT EXISTS stock_data.view_market_daily_review AS
SELECT 
    s.*, h.intensity, h.avg_premium, i.net_amount AS inst_net_amount, y.limit_success_rate, q.small_order_ratio
FROM market_review_daily_summary s
LEFT JOIN market_review_huijin h ON s.trade_date = h.trade_date
LEFT JOIN market_review_institution i ON s.trade_date = i.trade_date
LEFT JOIN market_review_yousi y ON s.trade_date = y.trade_date
LEFT JOIN market_review_quant q ON s.trade_date = q.trade_date;
```

## 3. 架构设计指导准则

1.  **单点主导**: 对于结论性、低频、小规模数据（< 100万行），强制在 Node 41 存储。
2.  **拒绝分片**: 禁止为小于 10MB 的数据集创建分布式表，以减少元数据同步开销和 IO 浪费。
3.  **按需解耦**: 物理表按业务原子性拆分，查询层透明合并。
