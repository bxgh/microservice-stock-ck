-- ClickHouse Initialization Script for EPIC-010
-- Create Database
CREATE DATABASE IF NOT EXISTS stock_data;

-- 日K线表
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

-- 财务数据表
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

-- 估值历史表
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

-- 因子值表
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
