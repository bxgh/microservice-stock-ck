-- ClickHouse 复权因子表结构
-- 基于 MySQL adj_factors 表设计

CREATE TABLE IF NOT EXISTS stock_adjust_factor
(
    stock_code String COMMENT '股票代码',
    ex_date Date COMMENT '除权日期',
    fore_factor Decimal(20, 10) COMMENT '前复权因子',
    back_factor Decimal(20, 10) COMMENT '后复权因子',
    update_time DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(update_time)
PARTITION BY toYear(ex_date)
ORDER BY (stock_code, ex_date)
SETTINGS index_granularity = 8192;

COMMENT ON TABLE stock_adjust_factor IS '股票复权因子表';
