-- ============================================
-- 任务 ID: [E2-S1-T2] - 修正版
-- 描述: 创建 ClickHouse 标注表 ads_l8_backtest_label
-- 规范: ReplacingMergeTree + 分布式表 + 指定数据库
-- ============================================

-- 1. 创建本地表
CREATE TABLE IF NOT EXISTS stock_data.ads_l8_backtest_label_local ON CLUSTER 'stock_cluster' (
    `id` UInt64,
    `ts_code` String,
    `trade_date` Date,
    `source_version` String,
    
    `ret_t1` Decimal(10, 6) DEFAULT 0,
    `ret_t5` Decimal(10, 6) DEFAULT 0,
    `ret_t10` Decimal(10, 6) DEFAULT 0,
    `ret_t20` Decimal(10, 6) DEFAULT 0,
    `ret_t30` Decimal(10, 6) DEFAULT 0,
    
    `benchmark_ret_t5` Decimal(10, 6) DEFAULT 0,
    `alpha_t5` Decimal(10, 6) DEFAULT 0,
    
    `market_regime` String DEFAULT '',
    `anomaly_category` String DEFAULT '',
    
    `created_at` DateTime,
    `updated_at` DateTime,
    `is_deleted` UInt8 DEFAULT 0
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, ts_code, source_version)
SETTINGS index_granularity = 8192;

-- 2. 创建分布式表
CREATE TABLE IF NOT EXISTS stock_data.ads_l8_backtest_label ON CLUSTER 'stock_cluster' 
AS stock_data.ads_l8_backtest_label_local
ENGINE = Distributed('stock_cluster', 'stock_data', 'ads_l8_backtest_label_local', rand());
