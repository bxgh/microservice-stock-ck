-- ============================================
-- 任务 ID: [E1-S9-T2]
-- 描述: 初始化筛选模板数据 (dim_filter_profile)
-- ============================================

INSERT INTO `dim_filter_profile` (`profile_code`, `profile_name`, `rules_json`, `is_system`) VALUES
('profile_default', '新手默认模式', '{"exclude_st": true, "min_days_listed": 60, "min_amount": 10000000, "exclude_new_stock": true}', 1),
('profile_short_term', '短线接力派', '{"focus_board": true, "min_resonance_level": 3, "prefer_sector_leader": true, "max_mcap": 20000000000}', 1),
('profile_value_observer', '中线机构派', '{"focus_inst_buy": true, "min_days_listed": 365, "min_ma250_dist": -0.05, "max_pe": 50}', 1),
('profile_sector_research', '板块研究派', '{"group_by_sector": true, "min_sector_resonance": 0.5, "weight_sector_factor": 1.5}', 1),
('profile_research_mode', '全量研究模式', '{"no_filter": true}', 1)
ON DUPLICATE KEY UPDATE 
    `profile_name` = VALUES(`profile_name`),
    `rules_json` = VALUES(`rules_json`),
    `is_system` = VALUES(`is_system`);
