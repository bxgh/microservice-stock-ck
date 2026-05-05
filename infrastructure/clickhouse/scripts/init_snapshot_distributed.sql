-- ============================================
-- ClickHouse 分布式快照表初始化脚本
-- 用途：支持全市场快照数据分片采集
-- 创建时间：2026-01-22
-- ============================================

-- ============================================
-- 步骤 1: 在每个节点创建本地表
-- ============================================

CREATE TABLE IF NOT EXISTS stock_data.snapshot_data_local ON CLUSTER stock_cluster (
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
COMMENT '股票盘口快照数据本地表';

-- ============================================
-- 步骤 2: 创建分布式表
-- ============================================

CREATE TABLE IF NOT EXISTS stock_data.snapshot_data_distributed ON CLUSTER stock_cluster (
    snapshot_time DateTime64(3) COMMENT '快照时间（毫秒精度）',
    trade_date Date COMMENT '交易日期',
    stock_code String COMMENT '股票代码（如 000001）',
    stock_name String COMMENT '股票名称',
    market String COMMENT '交易所（SH/SZ/BJ）',
    current_price Decimal(10, 3) COMMENT '当前价格',
    open_price Decimal(10, 3) COMMENT '开盘价',
    high_price Decimal(10, 3) COMMENT '最高价',
    low_price Decimal(10, 3) COMMENT '最低价',
    pre_close Decimal(10, 3) COMMENT '昨收价',
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
    total_volume UInt64 COMMENT '总成交量（手）',
    total_amount Decimal(18, 2) COMMENT '总成交额（元）',
    turnover_rate Decimal(8, 4) COMMENT '换手率（%）',
    data_source String DEFAULT 'mootdx' COMMENT '数据来源',
    pool_level String DEFAULT 'L1' COMMENT '股票池级别（L1/L2/L3）',
    created_at DateTime DEFAULT now() COMMENT '记录创建时间'
) ENGINE = Distributed('stock_cluster', 'stock_data', 'snapshot_data_local', xxHash64(stock_code))
COMMENT '股票盘口快照数据分布式表';

-- ============================================
-- 步骤 3: 验证表创建
-- ============================================

SELECT '✅ ClickHouse 分布式快照表初始化完成！' as status;
SELECT 'Local Table: snapshot_data_local' as info;
SELECT 'Distributed Table: snapshot_data_distributed' as info;
SELECT 'Sharding Key: xxHash64(stock_code)' as info;
