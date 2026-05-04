-- =============================================================================
-- ClickHouse 全量表结构定义 (Mirror of Tencent MySQL alwaysup)
-- 包含：行情、财务、事件、维度、ADS指标层
-- =============================================================================

CREATE DATABASE IF NOT EXISTS stock_data ON CLUSTER stock_cluster;

-- ---------------------------------------------------------
-- 1. 行情与指数核心表 (Market Data)
-- ---------------------------------------------------------

-- daily_basic
CREATE TABLE IF NOT EXISTS stock_data.daily_basic_local ON CLUSTER stock_cluster (
    ts_code String,
    trade_date Date,
    close Nullable(Float32),
    turnover_rate Nullable(Float32),
    turnover_rate_f Nullable(Float32),
    volume_ratio Nullable(Float32),
    pe Nullable(Float32),
    pe_ttm Nullable(Float32),
    pb Nullable(Float32),
    ps Nullable(Float32),
    ps_ttm Nullable(Float32),
    dv_ratio Nullable(Float32),
    dv_ttm Nullable(Float32),
    total_share Nullable(Float32),
    float_share Nullable(Float32),
    free_share Nullable(Float32),
    total_mv Nullable(Float32),
    circ_mv Nullable(Float32),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.daily_basic ON CLUSTER stock_cluster AS stock_data.daily_basic_local
ENGINE = Distributed(stock_cluster, stock_data, daily_basic_local, xxHash64(ts_code));

-- stock_kline_daily
CREATE TABLE IF NOT EXISTS stock_data.stock_kline_daily_local ON CLUSTER stock_cluster (
    ts_code String,
    trade_date Date,
    open Nullable(Float32),
    high Nullable(Float32),
    low Nullable(Float32),
    close Nullable(Float32),
    pre_close Nullable(Float32),
    volume Nullable(Int64),
    amount Nullable(Float64),
    turnover Nullable(Float32),
    pct_chg Nullable(Float32),
    trade_status Nullable(Int8),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.stock_kline_daily ON CLUSTER stock_cluster AS stock_data.stock_kline_daily_local
ENGINE = Distributed(stock_cluster, stock_data, stock_kline_daily_local, xxHash64(ts_code));

-- ods_index_daily
CREATE TABLE IF NOT EXISTS stock_data.ods_index_daily_local ON CLUSTER stock_cluster (
    trade_date Date,
    ts_code String,
    open Nullable(Float32),
    high Nullable(Float32),
    low Nullable(Float32),
    close Nullable(Float32),
    pre_close Nullable(Float32),
    change Nullable(Float32),
    pct_chg Nullable(Float32),
    vol Nullable(Float64),
    amount Nullable(Float64),
    data_source Nullable(String),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYear(trade_date)
ORDER BY (trade_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.ods_index_daily ON CLUSTER stock_cluster AS stock_data.ods_index_daily_local
ENGINE = Distributed(stock_cluster, stock_data, ods_index_daily_local, xxHash64(ts_code));

-- ods_sw_index_daily
CREATE TABLE IF NOT EXISTS stock_data.ods_sw_index_daily_local ON CLUSTER stock_cluster (
    trade_date Date,
    ts_code String,
    name Nullable(String),
    close Nullable(Float32),
    pct_chg Nullable(Float32),
    amount Nullable(Float64),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYear(trade_date)
ORDER BY (trade_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.ods_sw_index_daily ON CLUSTER stock_cluster AS stock_data.ods_sw_index_daily_local
ENGINE = Distributed(stock_cluster, stock_data, ods_sw_index_daily_local, xxHash64(ts_code));

-- ods_concept_kline_daily
CREATE TABLE IF NOT EXISTS stock_data.ods_concept_kline_daily_local ON CLUSTER stock_cluster (
    trade_date Date,
    concept_code String,
    concept_name Nullable(String),
    open Nullable(Float32),
    high Nullable(Float32),
    low Nullable(Float32),
    close Nullable(Float32),
    pct_chg Nullable(Float32),
    amount Nullable(Float64),
    up_count Nullable(Int32),
    down_count Nullable(Int32),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYear(trade_date)
ORDER BY (trade_date, concept_code);

CREATE TABLE IF NOT EXISTS stock_data.ods_concept_kline_daily ON CLUSTER stock_cluster AS stock_data.ods_concept_kline_daily_local
ENGINE = Distributed(stock_cluster, stock_data, ods_concept_kline_daily_local, xxHash64(concept_code));

-- sector_kline_daily
CREATE TABLE IF NOT EXISTS stock_data.sector_kline_daily_local ON CLUSTER stock_cluster (
    ts_code String,
    trade_date Date,
    open Nullable(Float32),
    high Nullable(Float32),
    low Nullable(Float32),
    close Nullable(Float32),
    volume Nullable(Float64),
    amount Nullable(Float64),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.sector_kline_daily ON CLUSTER stock_cluster AS stock_data.sector_kline_daily_local
ENGINE = Distributed(stock_cluster, stock_data, sector_kline_daily_local, xxHash64(ts_code));

-- ---------------------------------------------------------
-- 2. 财务与股东 (Financials & Shareholders)
-- ---------------------------------------------------------

-- stock_balance_sheet
CREATE TABLE IF NOT EXISTS stock_data.stock_balance_sheet_local ON CLUSTER stock_cluster (
    ts_code String,
    report_date Date,
    notice_date Nullable(Date),
    total_assets Nullable(Float64),
    total_liabilities Nullable(Float64),
    total_equity Nullable(Float64),
    monetary_funds Nullable(Float64),
    accounts_receivable Nullable(Float64),
    inventory Nullable(Float64),
    short_term_borrowings Nullable(Float64),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYear(report_date)
ORDER BY (report_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.stock_balance_sheet ON CLUSTER stock_cluster AS stock_data.stock_balance_sheet_local
ENGINE = Distributed(stock_cluster, stock_data, stock_balance_sheet_local, xxHash64(ts_code));

-- stock_income_statement
CREATE TABLE IF NOT EXISTS stock_data.stock_income_statement_local ON CLUSTER stock_cluster (
    ts_code String,
    report_date Date,
    notice_date Nullable(Date),
    total_revenue Nullable(Float64),
    operating_revenue Nullable(Float64),
    net_profit Nullable(Float64),
    parent_net_profit Nullable(Float64),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYear(report_date)
ORDER BY (report_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.stock_income_statement ON CLUSTER stock_cluster AS stock_data.stock_income_statement_local
ENGINE = Distributed(stock_cluster, stock_data, stock_income_statement_local, xxHash64(ts_code));

-- stock_cash_flow_statement
CREATE TABLE IF NOT EXISTS stock_data.stock_cash_flow_statement_local ON CLUSTER stock_cluster (
    ts_code String,
    report_date Date,
    notice_date Nullable(Date),
    net_operating_cash_flow Nullable(Float64),
    free_cash_flow Nullable(Float64),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYear(report_date)
ORDER BY (report_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.stock_cash_flow_statement ON CLUSTER stock_cluster AS stock_data.stock_cash_flow_statement_local
ENGINE = Distributed(stock_cluster, stock_data, stock_cash_flow_statement_local, xxHash64(ts_code));

-- stock_finance_indicators
CREATE TABLE IF NOT EXISTS stock_data.stock_finance_indicators_local ON CLUSTER stock_cluster (
    ts_code String,
    report_date Date,
    roe Nullable(Float32),
    roa Nullable(Float32),
    netprofit_margin Nullable(Float32),
    grossprofit_margin Nullable(Float32),
    asset_liab_ratio Nullable(Float32),
    current_ratio Nullable(Float32),
    eps Nullable(Float32),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYear(report_date)
ORDER BY (report_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.stock_finance_indicators ON CLUSTER stock_cluster AS stock_data.stock_finance_indicators_local
ENGINE = Distributed(stock_cluster, stock_data, stock_finance_indicators_local, xxHash64(ts_code));

-- stock_shareholder_count
CREATE TABLE IF NOT EXISTS stock_data.stock_shareholder_count_local ON CLUSTER stock_cluster (
    ts_code String,
    end_date Date,
    holder_count Nullable(Int32),
    holder_change_pct Nullable(Float32),
    avg_market_cap Nullable(Float64),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYear(end_date)
ORDER BY (end_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.stock_shareholder_count ON CLUSTER stock_cluster AS stock_data.stock_shareholder_count_local
ENGINE = Distributed(stock_cluster, stock_data, stock_shareholder_count_local, xxHash64(ts_code));

-- stock_top10_shareholders
CREATE TABLE IF NOT EXISTS stock_data.stock_top10_shareholders_local ON CLUSTER stock_cluster (
    ts_code String,
    end_date Date,
    rank Int32,
    holder_name Nullable(String),
    share_type Nullable(String),
    hold_count Nullable(Int64),
    hold_pct Nullable(Float32),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYear(end_date)
ORDER BY (end_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.stock_top10_shareholders ON CLUSTER stock_cluster AS stock_data.stock_top10_shareholders_local
ENGINE = Distributed(stock_cluster, stock_data, stock_top10_shareholders_local, xxHash64(ts_code));

-- stock_performance_forecast
CREATE TABLE IF NOT EXISTS stock_data.stock_performance_forecast_local ON CLUSTER stock_cluster (
    ts_code String,
    report_period Date,
    notice_date Date,
    type Nullable(String),
    growth_min Nullable(Float32),
    growth_max Nullable(Float32),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYear(report_period)
ORDER BY (report_period, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.stock_performance_forecast ON CLUSTER stock_cluster AS stock_data.stock_performance_forecast_local
ENGINE = Distributed(stock_cluster, stock_data, stock_performance_forecast_local, xxHash64(ts_code));

-- ---------------------------------------------------------
-- 3. 事件 (Events)
-- ---------------------------------------------------------

-- ods_event_limit_pool
CREATE TABLE IF NOT EXISTS stock_data.ods_event_limit_pool_local ON CLUSTER stock_cluster (
    trade_date Date,
    ts_code String,
    name Nullable(String),
    pool_type String,
    close Nullable(Float32),
    pct_chg Nullable(Float32),
    amount Nullable(Float64),
    circ_mv Nullable(Float64),
    turnover_rate Nullable(Float32),
    first_limit_time Nullable(String),
    last_limit_time Nullable(String),
    board_height Nullable(Int32),
    seal_money Nullable(Float64),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, pool_type, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.ods_event_limit_pool ON CLUSTER stock_cluster AS stock_data.ods_event_limit_pool_local
ENGINE = Distributed(stock_cluster, stock_data, ods_event_limit_pool_local, xxHash64(ts_code));

-- stock_lhb_daily
CREATE TABLE IF NOT EXISTS stock_data.stock_lhb_daily_local ON CLUSTER stock_cluster (
    ts_code String,
    trade_date Date,
    net_buy_amt Nullable(Float64),
    buy_amt Nullable(Float64),
    sell_amt Nullable(Float64),
    reason Nullable(String),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.stock_lhb_daily ON CLUSTER stock_cluster AS stock_data.stock_lhb_daily_local
ENGINE = Distributed(stock_cluster, stock_data, stock_lhb_daily_local, xxHash64(ts_code));

-- stock_block_trade
CREATE TABLE IF NOT EXISTS stock_data.stock_block_trade_local ON CLUSTER stock_cluster (
    ts_code String,
    trade_date Date,
    price Nullable(Float32),
    volume Nullable(Int64),
    amount Nullable(Float64),
    buyer Nullable(String),
    seller Nullable(String),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.stock_block_trade ON CLUSTER stock_cluster AS stock_data.stock_block_trade_local
ENGINE = Distributed(stock_cluster, stock_data, stock_block_trade_local, xxHash64(ts_code));

-- stock_suspensions
CREATE TABLE IF NOT EXISTS stock_data.stock_suspensions_local ON CLUSTER stock_cluster (
    ts_code String,
    trade_date Date,
    is_suspended Int8,
    reason Nullable(String),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.stock_suspensions ON CLUSTER stock_cluster AS stock_data.stock_suspensions_local
ENGINE = Distributed(stock_cluster, stock_data, stock_suspensions_local, xxHash64(ts_code));

-- stock_restricted_release
CREATE TABLE IF NOT EXISTS stock_data.stock_restricted_release_local ON CLUSTER stock_cluster (
    ts_code String,
    release_date Date,
    release_count Nullable(Int64),
    release_market_cap Nullable(Float64),
    ratio Nullable(Float32),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYear(release_date)
ORDER BY (release_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.stock_restricted_release ON CLUSTER stock_cluster AS stock_data.stock_restricted_release_local
ENGINE = Distributed(stock_cluster, stock_data, stock_restricted_release_local, xxHash64(ts_code));

-- ---------------------------------------------------------
-- 4. ADS & Monitoring
-- ---------------------------------------------------------

-- ads_l1_market_overview
CREATE TABLE IF NOT EXISTS stock_data.ads_l1_market_overview_local ON CLUSTER stock_cluster (
    trade_date Date,
    idx_sh_close Nullable(Float32),
    idx_sh_pct Nullable(Float32),
    turnover_total Nullable(Float64),
    up_count Nullable(Int32),
    down_count Nullable(Int32),
    market_regime Nullable(String),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYear(trade_date)
ORDER BY (trade_date);

CREATE TABLE IF NOT EXISTS stock_data.ads_l1_market_overview ON CLUSTER stock_cluster AS stock_data.ads_l1_market_overview_local
ENGINE = Distributed(stock_cluster, stock_data, ads_l1_market_overview_local, rand());

-- ads_l2_industry_daily
CREATE TABLE IF NOT EXISTS stock_data.ads_l2_industry_daily_local ON CLUSTER stock_cluster (
    trade_date Date,
    industry_code String,
    industry_name Nullable(String),
    close Nullable(Float32),
    pct_chg Nullable(Float32),
    amount Nullable(Float64),
    internal_breadth Nullable(Float32),
    top_stock_code Nullable(String),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, industry_code);

CREATE TABLE IF NOT EXISTS stock_data.ads_l2_industry_daily ON CLUSTER stock_cluster AS stock_data.ads_l2_industry_daily_local
ENGINE = Distributed(stock_cluster, stock_data, ads_l2_industry_daily_local, xxHash64(industry_code));

-- ads_stock_derived_metrics
CREATE TABLE IF NOT EXISTS stock_data.ads_stock_derived_metrics_local ON CLUSTER stock_cluster (
    trade_date Date,
    ts_code String,
    volume_ratio_5d Nullable(Float32),
    volume_ratio_20d Nullable(Float32),
    dist_to_ma20 Nullable(Float32),
    dist_to_ma250 Nullable(Float32),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, ts_code);

CREATE TABLE IF NOT EXISTS stock_data.ads_stock_derived_metrics ON CLUSTER stock_cluster AS stock_data.ads_stock_derived_metrics_local
ENGINE = Distributed(stock_cluster, stock_data, ads_stock_derived_metrics_local, xxHash64(ts_code));

-- monitor_health_scores
CREATE TABLE IF NOT EXISTS stock_data.monitor_health_scores_local ON CLUSTER stock_cluster (
    trade_date Date,
    total_score Nullable(Float32),
    status Nullable(String),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYear(trade_date)
ORDER BY (trade_date);

CREATE TABLE IF NOT EXISTS stock_data.monitor_health_scores ON CLUSTER stock_cluster AS stock_data.monitor_health_scores_local
ENGINE = Distributed(stock_cluster, stock_data, monitor_health_scores_local, rand());

-- ---------------------------------------------------------
-- 5. Dimensions
-- ---------------------------------------------------------

-- stock_basic_info
CREATE TABLE IF NOT EXISTS stock_data.stock_basic_info_local ON CLUSTER stock_cluster (
    ts_code String,
    symbol Nullable(String),
    name Nullable(String),
    area Nullable(String),
    industry Nullable(String),
    market Nullable(String),
    list_date Nullable(Date),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (ts_code);

CREATE TABLE IF NOT EXISTS stock_data.stock_basic_info ON CLUSTER stock_cluster AS stock_data.stock_basic_info_local
ENGINE = Distributed(stock_cluster, stock_data, stock_basic_info_local, xxHash64(ts_code));

-- index_basic
CREATE TABLE IF NOT EXISTS stock_data.index_basic_local ON CLUSTER stock_cluster (
    ts_code String,
    name Nullable(String),
    market Nullable(String),
    category Nullable(String),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (ts_code);

CREATE TABLE IF NOT EXISTS stock_data.index_basic ON CLUSTER stock_cluster AS stock_data.index_basic_local
ENGINE = Distributed(stock_cluster, stock_data, index_basic_local, xxHash64(ts_code));

-- trade_cal
CREATE TABLE IF NOT EXISTS stock_data.trade_cal_local ON CLUSTER stock_cluster (
    cal_date Date,
    exchange String,
    is_open Int8,
    pretrade_date Nullable(Date),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (cal_date, exchange);

CREATE TABLE IF NOT EXISTS stock_data.trade_cal ON CLUSTER stock_cluster AS stock_data.trade_cal_local
ENGINE = Distributed(stock_cluster, stock_data, trade_cal_local, rand());

-- stock_industry_sw
CREATE TABLE IF NOT EXISTS stock_data.stock_industry_sw_local ON CLUSTER stock_cluster (
    code String,
    l1_code Nullable(String),
    l1_name Nullable(String),
    l2_code Nullable(String),
    l2_name Nullable(String),
    l3_code Nullable(String),
    l3_name Nullable(String),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (code);

CREATE TABLE IF NOT EXISTS stock_data.stock_industry_sw ON CLUSTER stock_cluster AS stock_data.stock_industry_sw_local
ENGINE = Distributed(stock_cluster, stock_data, stock_industry_sw_local, xxHash64(code));

-- stock_sector_ths
CREATE TABLE IF NOT EXISTS stock_data.stock_sector_ths_local ON CLUSTER stock_cluster (
    id Int32,
    sector_name Nullable(String),
    sector_type Nullable(String),
    sector_level Nullable(String),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (id);

CREATE TABLE IF NOT EXISTS stock_data.stock_sector_ths ON CLUSTER stock_cluster AS stock_data.stock_sector_ths_local
ENGINE = Distributed(stock_cluster, stock_data, stock_sector_ths_local, rand());
