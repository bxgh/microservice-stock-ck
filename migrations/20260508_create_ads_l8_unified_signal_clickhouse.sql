-- ============================================
-- 任务 ID: [E1-S1-T2]
-- 描述: 创建 ads_l8_unified_signal ClickHouse 同步表
-- 规范: ReplacingMergeTree, 支持双写一致性
-- ============================================

-- 1. 创建本地表
CREATE TABLE IF NOT EXISTS stock_data.ads_l8_unified_signal_local
(
    `id`                UInt64,
    `source_version`    String DEFAULT 'v1',
    `user_id`           UInt64 DEFAULT 1,
    `trade_date`        Date,
    `ts_code`           String,
    `name`              String,
    `industry_sw1`      String,
    `industry_sw3`      String,
    
    `pool_type`         String,
    `signal_type`       String,
    `signal_subtype`    String,
    `anomaly_category`  String,
    
    `pct_chg`           Decimal(10, 6),
    `turnover_rate`     Decimal(10, 6),
    `volume_ratio_5d`   Decimal(10, 6),
    `amount`            Decimal(20, 2),
    `main_net_inflow`   Decimal(20, 2),
    
    `signal_features`   String, -- ClickHouse 存储 JSON 为 String
    `tags`              String,
    
    `resonance_level`       Int8,
    `resonance_dimensions`  String,
    `resonance_score`       Float32,
    `counter_signals`       String,
    `counter_signal_score`  Float32,
    `temporal_resonance`    String,
    
    `raw_score`         Decimal(6, 2),
    `score_l3_capital`  Decimal(6, 2),
    `score_l4_emotion`  Decimal(6, 2),
    `score_user_pref`   Decimal(6, 2),
    `score_dedup_pen`   Decimal(6, 2),
    `composite_score`   Decimal(6, 2),
    `component_score`   String,
    
    `excluded_reasons`  String,
    `default_visible`   Int8 DEFAULT 1,
    `is_pushed`         Int8 DEFAULT 1,
    `explanation_zh`    String,
    
    `extra`             String,
    `schema_version`    String DEFAULT 'v1.1',
    `compute_version`   String,
    
    `created_at`        DateTime DEFAULT now(),
    `updated_at`        DateTime DEFAULT now(),
    `is_deleted`        Int8 DEFAULT 0
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, ts_code, pool_type, signal_type)
SETTINGS index_granularity = 8192;

-- 2. 创建分布式表
CREATE TABLE IF NOT EXISTS stock_data.ads_l8_unified_signal
AS stock_data.ads_l8_unified_signal_local
ENGINE = Distributed('stock_cluster', 'stock_data', 'ads_l8_unified_signal_local', xxHash64(ts_code));
