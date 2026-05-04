#!/bin/bash

CH_CMD="docker exec -i microservice-stock-clickhouse clickhouse-client --user admin --password admin123"
MYSQL_CONN="'127.0.0.1:36301', 'alwaysup', '%s', 'root', 'alwaysup@888'"

sync_one() {
    local table=$1
    local columns=$2
    echo "============================================================"
    echo "开始独立同步大表: $table"
    echo "============================================================"
    
    $CH_CMD --query "TRUNCATE TABLE stock_data.$table ON CLUSTER stock_cluster"
    
    local mysql_func=$(printf "$MYSQL_CONN" "$table")
    local sql="SET max_partitions_per_insert_block = 2000; 
               SET receive_timeout = 7200; 
               SET send_timeout = 7200;
               INSERT INTO stock_data.$table ($columns) 
               SELECT $columns FROM mysql($mysql_func)"
    
    time $CH_CMD --multiquery --query "$sql"
    echo "完成: $table"
}

# 执行指定的同步任务
case $1 in
    "daily_basic")
        sync_one "daily_basic" "ts_code, trade_date, close, turnover_rate, turnover_rate_f, volume_ratio, pe, pe_ttm, pb, ps, ps_ttm, dv_ratio, dv_ttm, total_share, float_share, free_share, total_mv, circ_mv"
        ;;
    "stock_kline_daily")
        sync_one "stock_kline_daily" "ts_code, trade_date, open, high, low, close, pre_close, volume, amount, turnover, pct_chg, trade_status"
        ;;
    "ods_stock_factor_daily")
        sync_one "ods_stock_factor_daily" "ts_code, trade_date, adjust_factor"
        ;;
    *)
        echo "使用方法: ./sync_large_tables.sh [daily_basic|stock_kline_daily|ods_stock_factor_daily]"
        ;;
esac
