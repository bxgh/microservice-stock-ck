-- 优化后的数据库 Schema (Story 10.2+)
-- 目标：原始数据与复权因子解耦

-- 1. 原始K线表 (永远存储不复权数据)
CREATE TABLE IF NOT EXISTS kline_daily (
    stock_code VARCHAR(12) NOT NULL,
    trade_date DATE NOT NULL,
    open DECIMAL(16, 4),
    high DECIMAL(16, 4),
    low DECIMAL(16, 4),
    close DECIMAL(16, 4),
    volume BIGINT,
    amount DECIMAL(20, 4),
    pre_close DECIMAL(16, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (stock_code, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 复权因子表
CREATE TABLE IF NOT EXISTS adj_factors (
    stock_code VARCHAR(12) NOT NULL,
    ex_date DATE NOT NULL,        -- 除权日期
    fore_factor DECIMAL(20, 10), -- 前复权因子
    back_factor DECIMAL(20, 10), -- 后复权因子
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (stock_code, ex_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 数据同步进度表
CREATE TABLE IF NOT EXISTS sync_progress (
    stock_code VARCHAR(12) NOT NULL,
    data_type VARCHAR(20) NOT NULL, -- 'KLINE_DAILY', 'ADJ_FACTOR'
    start_date DATE,
    end_date DATE,
    last_sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'DONE', -- 'PENDING', 'DONE', 'ERROR'
    PRIMARY KEY (stock_code, data_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 这里的 View 将在应用层或 ClickHouse 中定义以实现高性能查询
-- SELECT k.*, k.close * a.fore_factor as close_adj 
-- FROM kline_daily k JOIN adj_factors a ON k.stock_code = a.stock_code AND k.trade_date >= a.ex_date
