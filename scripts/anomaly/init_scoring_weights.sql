-- ============================================
-- 任务 ID: [E1-S9-T3]
-- 描述: 初始化评分权重配置 (dim_anomaly_score_weight)
-- ============================================

INSERT INTO `dim_anomaly_score_weight` (`version`, `weight_key`, `weight_value`, `is_active`) VALUES
('v1.1', 'alpha_trend', 0.3000, 1),
('v1.1', 'beta_capital', 0.2000, 1),
('v1.1', 'gamma_resonance', 0.1500, 1),
('v1.1', 'epsilon_sentiment', 0.1000, 1),
('v1.1', 'zeta_volume', 0.1000, 1),
('v1.1', 'mu_user_pref', 0.1000, 1),
('v1.1', 'nu_market', 0.0500, 1)
ON DUPLICATE KEY UPDATE 
    `weight_value` = VALUES(`weight_value`),
    `is_active` = VALUES(`is_active`);
