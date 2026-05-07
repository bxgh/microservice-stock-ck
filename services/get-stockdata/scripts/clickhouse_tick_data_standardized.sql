-- ============================================
-- ClickHouse tick_data 标准化 DDL (Cluster 架构)
-- 用途：存储盘后全量同步的分笔数据
-- ============================================

CREATE DATABASE IF NOT EXISTS stock_data ON CLUSTER stock_cluster;

USE stock_data;

-- 1. 创建本地表 (Replicated MergeTree)
CREATE TABLE IF NOT EXISTS tick_data_local ON CLUSTER stock_cluster
(
    stock_code    String COMMENT '股票代码',
    trade_date    Date COMMENT '交易日期',
    tick_time     String COMMENT '分笔时间',
    price         Decimal(10, 3) COMMENT '成交价格',
    volume        UInt32 COMMENT '成交量',
    amount        Decimal(18, 2) COMMENT '成交额',
    direction     UInt8 COMMENT '0=买 1=卖 2=中性',
    num           UInt32 DEFAULT 0 COMMENT '成交笔数',
    created_at    DateTime DEFAULT now() COMMENT '入库时间'
) ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/stock_data/tick_data_local', '{replica}', created_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, trade_date, tick_time, price, volume)
TTL trade_date + INTERVAL 365 DAY
SETTINGS index_granularity = 8192;

-- 2. 创建分布式视图 (Distributed)
CREATE TABLE IF NOT EXISTS tick_data ON CLUSTER stock_cluster
AS tick_data_local
ENGINE = Distributed(stock_cluster, stock_data, tick_data_local, rand());

-- 3. 创建索引加速查询
ALTER TABLE tick_data_local ON CLUSTER stock_cluster
ADD INDEX idx_stock_code stock_code TYPE bloom_filter GRANULARITY 1;

ALTER TABLE tick_data_local ON CLUSTER stock_cluster
ADD INDEX idx_trade_date trade_date TYPE minmax GRANULARITY 1;

-- 4. 创建每日统计物化视图 (SummingMergeTree)
CREATE MATERIALIZED VIEW IF NOT EXISTS tick_daily_stats_local ON CLUSTER stock_cluster
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, trade_date)
AS SELECT
    stock_code,
    trade_date,
    count() as tick_count,
    min(price) as low_price,
    max(price) as high_price,
    sum(volume) as total_volume,
    sum(amount) as total_amount,
    sumIf(volume, direction = 0) as buy_volume,
    sumIf(volume, direction = 1) as sell_volume,
    sumIf(amount, direction = 0) as buy_amount,
    sumIf(amount, direction = 1) as sell_amount
FROM tick_data_local
GROUP BY stock_code, trade_date;

-- 5. 分布式统计视图
CREATE TABLE IF NOT EXISTS tick_daily_stats ON CLUSTER stock_cluster
AS tick_daily_stats_local
ENGINE = Distributed(stock_cluster, stock_data, tick_daily_stats_local, rand());

SELECT '✅ ClickHouse 盘后分笔存储层初始化完成' as status;
