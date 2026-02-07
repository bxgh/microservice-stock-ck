-- EPIC-002 Part 2: 聚类分析结果存储表
-- 存储路径: services/quant-strategy/scripts/sql/create_analysis_results.sql

CREATE TABLE IF NOT EXISTS analysis_results (
    trade_date Date,                   -- 交易日期
    cluster_id UInt32,                 -- 聚类 ID
    members Array(String),             -- 成员股票代码列表
    leaders Array(Tuple(String, Float64)), -- 龙头股及其 PageRank 分数: [(code, score), ...]
    avg_divergence Float64,            -- 分歧度 (Rolling Std Mean)
    member_count UInt32,               -- 成员总数
    trend_phase String,                -- 趋势阶段 (Formation/Steady/Dissolution)
    updated_at DateTime DEFAULT now()  -- 更新时间
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (trade_date, cluster_id)
COMMENT '分笔数据策略-相关性聚类分析结果表';
