-- ============================================
-- 任务 ID: [E1-S1-T1]
-- 描述: 改造 ads_l8_unified_signal 增加极简版 v1 评估字段
-- 规范: MySQL 5.7, 增量添加字段及索引
-- ============================================

ALTER TABLE `ads_l8_unified_signal`
  ADD COLUMN `source_version` VARCHAR(16) NOT NULL DEFAULT 'v1' COMMENT '评分公式版本号' AFTER `id`,
  ADD COLUMN `anomaly_category` VARCHAR(8) DEFAULT NULL COMMENT '机制分类:C1/C2/C3/C4' AFTER `signal_subtype`,
  ADD COLUMN `component_score` JSON DEFAULT NULL COMMENT '评分分量溯源 JSON' AFTER `composite_score`,
  ADD COLUMN `is_pushed` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否推送(极端市况置 0)' AFTER `default_visible`,
  ADD KEY `idx_category_pushed` (`trade_date`, `anomaly_category`, `is_pushed`);

-- 历史数据初始化 (确保所有历史记录版本为 v1 且默认推送)
-- 注意: 如果表很大, 建议分批执行
UPDATE `ads_l8_unified_signal`
SET `source_version` = 'v1',
    `is_pushed` = 1
WHERE `source_version` IS NULL OR `source_version` = '';
