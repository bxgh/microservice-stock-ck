-- ============================================
-- ClickHouse 数据库初始化脚本
-- 用途：创建股票盘口快照数据存储表
-- 创建时间：2025-11-29
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS stock_data;

USE stock_data;

-- ============================================
-- 表1: 盘口快照数据表 (snapshot_data)
-- 用途：存储5档盘口实时快照，支持高频策略分析
-- 频率：L1池 3秒/轮，L2池 15秒/轮
-- ============================================

CREATE TABLE IF NOT EXISTS snapshot_data (
    -- ==================== 时间维度 ====================
    snapshot_time DateTime64(3) COMMENT '快照时间（毫秒精度）',
    trade_date Date COMMENT '交易日期',
    
    -- ==================== 股票维度 ====================
    stock_code String COMMENT '股票代码（如 000001）',
    stock_name String COMMENT '股票名称',
    market String COMMENT '交易所（SH/SZ/BJ）',
    
    -- ==================== 当前行情 ====================
    current_price Decimal(10, 3) COMMENT '当前价格',
    open_price Decimal(10, 3) COMMENT '开盘价',
    high_price Decimal(10, 3) COMMENT '最高价',
    low_price Decimal(10, 3) COMMENT '最低价',
    pre_close Decimal(10, 3) COMMENT '昨收价',
    
    -- ==================== 买五档 ====================
    bid_price1 Decimal(10, 3) COMMENT '买一价',
    bid_volume1 UInt32 COMMENT '买一量（手）',
    bid_price2 Decimal(10, 3) COMMENT '买二价',
    bid_volume2 UInt32 COMMENT '买二量（手）',
    bid_price3 Decimal(10, 3) COMMENT '买三价',
    bid_volume3 UInt32 COMMENT '买三量（手）',
    bid_price4 Decimal(10, 3) COMMENT '买四价',
    bid_volume4 UInt32 COMMENT '买四量（手）',
    bid_price5 Decimal(10, 3) COMMENT '买五价',
    bid_volume5 UInt32 COMMENT '买五量（手）',
    
    -- ==================== 卖五档 ====================
    ask_price1 Decimal(10, 3) COMMENT '卖一价',
    ask_volume1 UInt32 COMMENT '卖一量（手）',
    ask_price2 Decimal(10, 3) COMMENT '卖二价',
    ask_volume2 UInt32 COMMENT '卖二量（手）',
    ask_price3 Decimal(10, 3) COMMENT '卖三价',
    ask_volume3 UInt32 COMMENT '卖三量（手）',
    ask_price4 Decimal(10, 3) COMMENT '卖四价',
    ask_volume4 UInt32 COMMENT '卖四量（手）',
    ask_price5 Decimal(10, 3) COMMENT '卖五价',
    ask_volume5 UInt32 COMMENT '卖五量（手）',
    
    -- ==================== 成交统计 ====================
    total_volume UInt64 COMMENT '总成交量（手）',
    total_amount Decimal(18, 2) COMMENT '总成交额（元）',
    turnover_rate Decimal(8, 4) COMMENT '换手率（%）',
    
    -- ==================== 元数据 ====================
    data_source String DEFAULT 'mootdx' COMMENT '数据来源',
    pool_level String DEFAULT 'L1' COMMENT '股票池级别（L1/L2/L3）',
    created_at DateTime DEFAULT now() COMMENT '记录创建时间'
    
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(trade_date)  -- 按月分区，便于管理和查询优化
ORDER BY (stock_code, snapshot_time)  -- 按股票+时间排序，支持时间序列查询
TTL trade_date + INTERVAL 90 DAY  -- 90天后自动删除（热数据保留期）
SETTINGS index_granularity = 8192
COMMENT '股票盘口快照数据表';

-- ============================================
-- 创建物化视图：每日快照统计
-- 用途：加速聚合查询
-- ============================================

CREATE MATERIALIZED VIEW IF NOT EXISTS snapshot_daily_stats
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, trade_date)
AS SELECT
    stock_code,
    stock_name,
    trade_date,
    count() as snapshot_count,  -- 快照数量
    min(current_price) as min_price,
    max(current_price) as max_price,
    avg(current_price) as avg_price,
    sum(total_volume) as daily_volume,
    sum(total_amount) as daily_amount
FROM snapshot_data
GROUP BY stock_code, stock_name, trade_date;

-- ============================================
-- 创建索引：加速股票代码查询
-- ============================================

ALTER TABLE snapshot_data 
ADD INDEX idx_stock_code stock_code TYPE bloom_filter GRANULARITY 1;

-- ============================================
-- 授权（可选，根据安全需求调整）
-- ============================================

-- 创建只读用户
-- CREATE USER IF NOT EXISTS reader IDENTIFIED BY 'reader_password';
-- GRANT SELECT ON stock_data.* TO reader;

-- 创建读写用户
-- CREATE USER IF NOT EXISTS writer IDENTIFIED BY 'writer_password';
-- GRANT SELECT, INSERT ON stock_data.* TO writer;

-- ============================================
-- 初始化完成
-- ============================================

SELECT '✅ ClickHouse初始化完成！' as status;
SELECT 'Database: stock_data' as info;
SELECT 'Table: snapshot_data' as info;
SELECT 'View: snapshot_daily_stats' as info;
