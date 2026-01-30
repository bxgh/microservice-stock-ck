-- ============================================
-- ClickHouse tick_data 表 DDL
-- 用途：存储盘后分笔（Tick）数据
-- 创建时间：2026-01-06
-- ============================================

-- 使用现有数据库
USE stock_data;

-- ============================================
-- 分笔数据表 (tick_data)
-- 用途：存储历史分笔成交数据，支持量化策略分析
-- 数据来源：mootdx 盘后采集
-- ============================================

CREATE TABLE IF NOT EXISTS tick_data
(
    -- ==================== 主键维度 ====================
    stock_code    String COMMENT '股票代码（如 000001）',
    trade_date    Date COMMENT '交易日期',
    tick_time     String COMMENT '分笔时间（HH:MM 或 HH:MM:SS）',
    
    -- ==================== 成交数据 ====================
    price         Decimal(10, 3) COMMENT '成交价格',
    volume        UInt32 COMMENT '成交量（股）',
    amount        Decimal(18, 2) COMMENT '成交额（元）',
    
    -- ==================== 买卖方向 ====================
    -- 0: 买盘, 1: 卖盘, 2: 中性（集合竞价）
    direction     UInt8 COMMENT '买卖方向（0=买 1=卖 2=中性）',
    
    num           UInt32 DEFAULT 0 COMMENT '成交笔数',
    
    -- ==================== 元数据 ====================
    created_at    DateTime DEFAULT now() COMMENT '入库时间'
    
) ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/stock_data/tick_data', '{replica}', created_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, trade_date, tick_time, price, volume)
TTL trade_date + INTERVAL 365 DAY
SETTINGS index_granularity = 8192
COMMENT '股票分笔成交数据表';

-- ============================================
-- 添加索引加速查询
-- ============================================

ALTER TABLE tick_data 
ADD INDEX idx_stock_code stock_code TYPE bloom_filter GRANULARITY 1;

ALTER TABLE tick_data 
ADD INDEX idx_trade_date trade_date TYPE minmax GRANULARITY 1;

-- ============================================
-- 创建每日统计物化视图
-- ============================================

CREATE MATERIALIZED VIEW IF NOT EXISTS tick_daily_stats
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
    -- 买卖统计
    sumIf(volume, direction = 0) as buy_volume,
    sumIf(volume, direction = 1) as sell_volume,
    sumIf(amount, direction = 0) as buy_amount,
    sumIf(amount, direction = 1) as sell_amount
FROM tick_data
GROUP BY stock_code, trade_date;

-- ============================================
-- 初始化完成
-- ============================================

SELECT '✅ tick_data 表创建完成' as status;
