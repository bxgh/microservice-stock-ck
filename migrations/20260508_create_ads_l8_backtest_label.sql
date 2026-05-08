-- ============================================
-- 任务 ID: [E2-S1-T1]
-- 描述: 创建 L8 评估标注表 ads_l8_backtest_label
-- 规范: MySQL 5.7, 包含三件套, utf8mb4
-- ============================================

CREATE TABLE IF NOT EXISTS `ads_l8_backtest_label` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `ts_code` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `trade_date` DATE NOT NULL COMMENT '推送日期(T日)',
    `source_version` VARCHAR(16) NOT NULL DEFAULT 'v1' COMMENT '评分公式版本',
    
    -- T+N 收益率 (小数格式, 0.0123 = 1.23%)
    `ret_t1` DECIMAL(10, 6) NULL COMMENT 'T+1日收盘相对T日收盘收益率',
    `ret_t5` DECIMAL(10, 6) NULL COMMENT 'T+5日收盘相对T日收盘收益率',
    `ret_t10` DECIMAL(10, 6) NULL COMMENT 'T+10日收盘相对T日收盘收益率',
    `ret_t20` DECIMAL(10, 6) NULL COMMENT 'T+20日收盘相对T日收盘收益率',
    `ret_t30` DECIMAL(10, 6) NULL COMMENT 'T+30日收盘相对T日收盘收益率',
    
    -- 基准与超额
    `benchmark_ret_t5` DECIMAL(10, 6) NULL COMMENT '同期沪深300(985.SH)收益率',
    `alpha_t5` DECIMAL(10, 6) NULL COMMENT '超额收益 (ret_t5 - benchmark_ret_t5)',
    
    -- 辅助环境信息
    `market_regime` VARCHAR(16) NULL COMMENT '推送日市场状态 (如 BULL/BEAR/SIDEWAYS)',
    `anomaly_category` VARCHAR(8) NULL COMMENT '机制分类 (C1-C4)',
    
    -- 三件套
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
    
    -- 索引
    UNIQUE KEY `uk_code_date_version` (`ts_code`, `trade_date`, `source_version`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_updated_at` (`updated_at`),
    KEY `idx_category` (`anomaly_category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='L8异动推送效果标注表';
