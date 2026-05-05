-- ClickHouse K线日线表结构
-- 基于MySQL stock_kline_daily表设计

CREATE TABLE IF NOT EXISTS stock_kline_daily
(
    stock_code String COMMENT '股票代码（6位）',
    trade_date Date COMMENT '交易日期',
    open_price Float64 COMMENT '开盘价',
    high_price Float64 COMMENT '最高价',
    low_price Float64 COMMENT '最低价',
    close_price Float64 COMMENT '收盘价',
    volume UInt64 COMMENT '成交量（股）',
    amount Float64 COMMENT '成交额（元）',
    turnover_rate Nullable(Float32) COMMENT '换手率（%）',
    change_pct Nullable(Float32) COMMENT '涨跌幅（%）',
    create_time DateTime DEFAULT now() COMMENT '创建时间',
    update_time DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(update_time)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, trade_date)
SETTINGS index_granularity = 8192;

-- 创建索引以优化查询
-- ClickHouse会自动基于ORDER BY创建主键索引

COMMENT ON TABLE stock_kline_daily IS 'A股日线K线数据表';

-- 查询示例
-- SELECT * FROM stock_kline_daily 
-- WHERE stock_code = '600519' 
--   AND trade_date BETWEEN '2024-01-01' AND '2024-01-31'
-- ORDER BY trade_date;
