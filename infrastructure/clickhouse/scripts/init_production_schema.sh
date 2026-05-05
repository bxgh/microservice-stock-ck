#!/bin/bash
# init_production_schema.sh
# 初始化ClickHouse生产环境表结构

set -e

CLICKHOUSE_USER="admin"
CLICKHOUSE_PASSWORD="admin123"

echo "===== 初始化 ClickHouse 生产环境 ====="
echo ""

# 创建 tick_data 表（带复制）
echo "[1/3] 创建 tick_data 表..."
docker exec microservice-stock-clickhouse clickhouse-client --user $CLICKHOUSE_USER --password $CLICKHOUSE_PASSWORD <<EOF
USE stock_data;

CREATE TABLE IF NOT EXISTS tick_data
(
    stock_code    String COMMENT '股票代码',
    trade_date    Date COMMENT '交易日期',
    tick_time     String COMMENT '分笔时间',
    price         Decimal(10, 3) COMMENT '成交价格',
    volume        UInt32 COMMENT '成交量（股）',
    amount        Decimal(18, 2) COMMENT '成交额（元）',
    direction     UInt8 COMMENT '买卖方向（0=买 1=卖 2=中性）',
    created_at    DateTime DEFAULT now() COMMENT '入库时间'
) ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/stock_data/tick_data', '{replica}', created_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, trade_date, tick_time, price, volume)
TTL trade_date + INTERVAL 365 DAY
SETTINGS index_granularity = 8192;
EOF

echo "✓ tick_data 表已创建"

# 创建 K线表
echo ""
echo "[2/3] 创建 stock_kline_daily 表..."
docker exec microservice-stock-clickhouse clickhouse-client --user $CLICKHOUSE_USER --password $CLICKHOUSE_PASSWORD <<EOF
USE stock_data;

CREATE TABLE IF NOT EXISTS stock_kline_daily
(
    stock_code String COMMENT '股票代码',
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
) ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/stock_data/stock_kline_daily', '{replica}', update_time)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, trade_date)
SETTINGS index_granularity = 8192;
EOF

echo "✓ stock_kline_daily 表已创建"

# 创建 snapshot 表
echo ""
echo "[3/3] 创建 snapshot_data 表..."
docker exec microservice-stock-clickhouse clickhouse-client --user $CLICKHOUSE_USER --password $CLICKHOUSE_PASSWORD <<EOF
USE stock_data;

CREATE TABLE IF NOT EXISTS snapshot_data (
    snapshot_time DateTime64(3) COMMENT '快照时间',
    trade_date Date COMMENT '交易日期',
    stock_code String COMMENT '股票代码',
    stock_name String COMMENT '股票名称',
    market String COMMENT '交易所',
    current_price Decimal(10, 3) COMMENT '当前价格',
    total_volume UInt64 COMMENT '总成交量',
    total_amount Decimal(18, 2) COMMENT '总成交额',
    data_source String DEFAULT 'mootdx' COMMENT '数据来源',
    created_at DateTime DEFAULT now() COMMENT '记录创建时间'
) ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/stock_data/snapshot_data', '{replica}')
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, snapshot_time)
TTL trade_date + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;
EOF

echo "✓ snapshot_data 表已创建"

echo ""
echo "===== 验证表创建 ====="
docker exec microservice-stock-clickhouse clickhouse-client --user $CLICKHOUSE_USER --password $CLICKHOUSE_PASSWORD --query "SELECT name, engine FROM system.tables WHERE database='stock_data' ORDER BY name FORMAT PrettyCompact"

echo ""
echo "===== 初始化完成！====="
echo "数据库: stock_data"
echo "表列表:"
echo "  - tick_data (分笔数据)"
echo "  - stock_kline_daily (日K线)"
echo "  - snapshot_data (盘口快照)"
