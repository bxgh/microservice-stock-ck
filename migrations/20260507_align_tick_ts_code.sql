CREATE TABLE stock_data.tick_data_local
(
    `ts_code` String COMMENT '股票代码',
    `trade_date` Date COMMENT '交易日期',
    `tick_time` String COMMENT '分笔时间',
    `price` Decimal(10, 3) COMMENT '成交价格',
    `volume` UInt32 COMMENT '成交量',
    `amount` Decimal(18, 2) COMMENT '成交额',
    `direction` UInt8 COMMENT '0=买 1=卖 2=中性',
    `num` UInt32 DEFAULT 0 COMMENT '成交笔数',
    `created_at` DateTime DEFAULT now() COMMENT '入库时间',
    INDEX idx_ts_code ts_code TYPE bloom_filter GRANULARITY 1,
    INDEX idx_trade_date trade_date TYPE minmax GRANULARITY 1
)
ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/stock_data/tick_data_local', '{replica}', created_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (ts_code, trade_date, tick_time, price, volume)
TTL trade_date + toIntervalDay(365)
SETTINGS index_granularity = 8192;

CREATE TABLE stock_data.tick_data
(
    `ts_code` String COMMENT '股票代码',
    `trade_date` Date COMMENT '交易日期',
    `tick_time` String COMMENT '分笔时间',
    `price` Decimal(10, 3) COMMENT '成交价格',
    `volume` UInt32 COMMENT '成交量',
    `amount` Decimal(18, 2) COMMENT '成交额',
    `direction` UInt8 COMMENT '0=买 1=卖 2=中性',
    `num` UInt32 DEFAULT 0 COMMENT '成交笔数',
    `created_at` DateTime DEFAULT now() COMMENT '入库时间'
)
ENGINE = Distributed('stock_cluster', 'stock_data', 'tick_data_local', rand());

CREATE MATERIALIZED VIEW stock_data.tick_daily_stats_local
(
    `ts_code` String,
    `trade_date` Date,
    `tick_count` UInt64,
    `low_price` Decimal(10, 3),
    `high_price` Decimal(10, 3),
    `total_volume` UInt64,
    `total_amount` Decimal(38, 2),
    `buy_volume` UInt64,
    `sell_volume` UInt64,
    `buy_amount` Decimal(38, 2),
    `sell_amount` Decimal(38, 2)
)
ENGINE = SummingMergeTree
PARTITION BY toYYYYMM(trade_date)
ORDER BY (ts_code, trade_date)
SETTINGS index_granularity = 8192
AS SELECT
    ts_code,
    trade_date,
    count() AS tick_count,
    min(price) AS low_price,
    max(price) AS high_price,
    sum(volume) AS total_volume,
    sum(amount) AS total_amount,
    sumIf(volume, direction = 0) AS buy_volume,
    sumIf(volume, direction = 1) AS sell_volume,
    sumIf(amount, direction = 0) AS buy_amount,
    sumIf(amount, direction = 1) AS sell_amount
FROM stock_data.tick_data_local
GROUP BY
    ts_code,
    trade_date;

CREATE TABLE stock_data.tick_daily_stats
(
    `ts_code` String,
    `trade_date` Date,
    `tick_count` UInt64,
    `low_price` Decimal(10, 3),
    `high_price` Decimal(10, 3),
    `total_volume` UInt64,
    `total_amount` Decimal(38, 2),
    `buy_volume` UInt64,
    `sell_volume` UInt64,
    `buy_amount` Decimal(38, 2),
    `sell_amount` Decimal(38, 2)
)
ENGINE = Distributed('stock_cluster', 'stock_data', 'tick_daily_stats_local', rand());
