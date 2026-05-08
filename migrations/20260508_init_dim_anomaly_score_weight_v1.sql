-- ============================================
-- 任务 ID: [E1-S2-T2]
-- 描述: 初始化 dim_anomaly_score_weight v1 版权重数据
-- 规范: MySQL 5.7, 支持版本化切换
-- ============================================

-- 1. 清理可能存在的旧 v1 数据 (幂等性)
DELETE FROM `dim_anomaly_score_weight` WHERE `version` = 'v1';

-- 2. 插入极简版 v1 权重配置
INSERT INTO `dim_anomaly_score_weight` 
  (`version`, `weight_key`, `weight_value`, `is_active`, `created_at`)
VALUES
  ('v1', 'score_pct_chg', 0.3000, 1, NOW()),
  ('v1', 'score_volume',  0.3000, 1, NOW()),
  ('v1', 'score_event',   0.2000, 1, NOW()),
  ('v1', 'score_position', 0.2000, 1, NOW()),
  -- 元信息权重 (可选，用于记录总分校验基准)
  ('v1', 'weighted_total', 1.0000, 1, NOW());

-- 3. 验证
SELECT * FROM `dim_anomaly_score_weight` WHERE `version` = 'v1';
