#!/bin/bash

# =============================================================================
# ClickHouse 小表批量同步脚本 (排除 K线与 DailyBasic)
# =============================================================================

CH_CMD="docker exec -i microservice-stock-clickhouse clickhouse-client --user admin --password admin123"
MYSQL_CONN="'127.0.0.1:36301', 'alwaysup', '%s', 'root', 'alwaysup@888'"

sync_table() {
    local mysql_table=$1
    local ch_table=$2
    local columns=$3
    
    echo "------------------------------------------------------------"
    echo "正在同步: $mysql_table -> $ch_table"
    
    # 每次同步前清理，防止中断重试导致重复
    $CH_CMD --query "TRUNCATE TABLE stock_data.$ch_table ON CLUSTER stock_cluster"
    
    # 使用 mysql() 表函数直接拉取
    local mysql_func=$(printf "$MYSQL_CONN" "$mysql_table")
    
    # 增加超时阈值 (1小时) 和分区限制
    local sql="SET max_partitions_per_insert_block = 2000; 
               SET receive_timeout = 3600; 
               SET send_timeout = 3600;
               INSERT INTO stock_data.$ch_table ($columns) 
               SELECT $columns FROM mysql($mysql_func)"
    
    if $CH_CMD --multiquery --query "$sql"; then
        echo "成功完成: $ch_table"
    else
        echo "!!! 失败: $ch_table，尝试重试..."
        sleep 5
        $CH_CMD --multiquery --query "$sql"
    fi
    
    sleep 2
}

echo "开始批量同步小表业务数据 (排除大表)..."

# 1. 基础维表
sync_table "stock_basic_info" "stock_basic_info" "ts_code, symbol, name, area, industry, market, list_date"
sync_table "index_basic" "index_basic" "ts_code, name, market, category"
sync_table "trade_cal" "trade_cal" "cal_date, exchange, is_open, pretrade_date"
sync_table "stock_industry_sw" "stock_industry_sw" "code, l1_code, l1_name, l2_code, l2_name, l3_code, l3_name"
sync_table "stock_sector_ths" "stock_sector_ths" "id, sector_name, sector_type, sector_level"

# 2. 行情核心表 (排除 daily_basic 和 stock_kline_daily)
sync_table "ods_index_daily" "ods_index_daily" "trade_date, ts_code, open, high, low, close, pre_close, change, pct_chg, vol, amount, data_source"
sync_table "ods_sw_index_daily" "ods_sw_index_daily" "trade_date, ts_code, name, close, pct_chg, amount"
sync_table "ods_concept_kline_daily" "ods_concept_kline_daily" "trade_date, concept_code, concept_name, open, high, low, close, pct_chg, amount, up_count, down_count"
sync_table "sector_kline_daily" "sector_kline_daily" "ts_code, trade_date, open, high, low, close, volume, amount"

# 3. 财务与股东
sync_table "stock_balance_sheet" "stock_balance_sheet" "ts_code, report_date, notice_date, total_assets, total_liabilities, total_equity, monetary_funds, accounts_receivable, inventory, short_term_borrowings"
sync_table "stock_income_statement" "stock_income_statement" "ts_code, report_date, notice_date, total_revenue, operating_revenue, net_profit, parent_net_profit"
sync_table "stock_cash_flow_statement" "stock_cash_flow_statement" "ts_code, report_date, notice_date, net_operating_cash_flow, free_cash_flow"
sync_table "stock_finance_indicators" "stock_finance_indicators" "ts_code, report_date, roe, roa, netprofit_margin, grossprofit_margin, asset_liab_ratio, current_ratio, eps"
sync_table "stock_shareholder_count" "stock_shareholder_count" "ts_code, end_date, holder_count, holder_change_pct, avg_market_cap"
sync_table "stock_top10_shareholders" "stock_top10_shareholders" "ts_code, end_date, rank, holder_name, share_type, hold_count, hold_pct"
sync_table "stock_performance_forecast" "stock_performance_forecast" "ts_code, report_period, notice_date, type, growth_min, growth_max"

# 4. 市场事件
sync_table "ods_event_limit_pool" "ods_event_limit_pool" "trade_date, ts_code, name, pool_type, close, pct_chg, amount, circ_mv, turnover_rate, first_limit_time, last_limit_time, board_height, seal_money"
sync_table "stock_lhb_daily" "stock_lhb_daily" "ts_code, trade_date, net_buy_amt, buy_amt, sell_amt, reason"
sync_table "stock_block_trade" "stock_block_trade" "ts_code, trade_date, price, volume, amount, buyer, seller"
sync_table "stock_suspensions" "stock_suspensions" "ts_code, trade_date, is_suspended, reason"
sync_table "stock_restricted_release" "stock_restricted_release" "ts_code, release_date, release_count, release_market_cap, ratio"

# 5. ADS 指标层
sync_table "ads_l1_market_overview" "ads_l1_market_overview" "trade_date, idx_sh_close, idx_sh_pct, turnover_total, up_count, down_count, market_regime"
sync_table "ads_l2_industry_daily" "ads_l2_industry_daily" "trade_date, industry_code, industry_name, close, pct_chg, amount, internal_breadth, top_stock_code"
sync_table "ads_stock_derived_metrics" "ads_stock_derived_metrics" "trade_date, ts_code, volume_ratio_5d, volume_ratio_20d, dist_to_ma20, dist_to_ma250"
sync_table "monitor_health_scores" "monitor_health_scores" "trade_date, total_score, status"

echo "============================================================"
echo "小表批量同步完成！"
echo "============================================================"
