-- ============================================
-- 任务 ID: [E1-S2-T1]
-- 描述: 创建异动信号统一池表 ads_l8_unified_signal
-- 规范: MySQL 5.7, 包含软删除、JSON 字段及唯一键约束
-- ============================================

CREATE TABLE IF NOT EXISTS `ads_l8_unified_signal` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`           BIGINT UNSIGNED NOT NULL DEFAULT 1,
  `trade_date`        DATE            NOT NULL,
  `ts_code`           VARCHAR(20)     NOT NULL,
  `name`              VARCHAR(50)     NOT NULL,
  `industry_sw1`      VARCHAR(50),
  `industry_sw3`      VARCHAR(50),
  
  -- 类型
  `pool_type`         VARCHAR(16)     NOT NULL                  COMMENT 'strong/early/trap',
  `signal_type`       VARCHAR(40)     NOT NULL,
  `signal_subtype`    VARCHAR(40),
  
  -- 行情与特征
  `pct_chg`           DECIMAL(10,6),
  `turnover_rate`     DECIMAL(10,6),
  `volume_ratio_5d`   DECIMAL(10,6),
  `amount`            DECIMAL(20,2),
  `main_net_inflow`   DECIMAL(20,2),
  `signal_features`   JSON                                        COMMENT '差异化指标',
  `tags`              JSON                                        COMMENT '多维度标签',
  
  -- 印证评估
  `resonance_level`       TINYINT                                COMMENT '共振等级 1-5',
  `resonance_dimensions`  JSON                                    COMMENT '共振维度详情',
  `resonance_score`       DECIMAL(6,2),
  `counter_signals`       JSON                                    COMMENT '反向信号',
  `counter_signal_score`  DECIMAL(6,2),
  `temporal_resonance`    JSON                                    COMMENT '时间窗口共振',
  
  -- 评分
  `raw_score`         DECIMAL(6,2),
  `score_l3_capital`  DECIMAL(6,2),
  `score_l4_emotion`  DECIMAL(6,2),
  `score_user_pref`   DECIMAL(6,2),
  `score_dedup_pen`   DECIMAL(6,2),
  `composite_score`   DECIMAL(6,2)                                COMMENT '综合评分',
  
  -- 弹性设计
  `excluded_reasons`  JSON                                        COMMENT '排除理由',
  `default_visible`   TINYINT(1)      DEFAULT 1,
  `explanation_zh`    VARCHAR(500)                                COMMENT '中文解释',
  
  -- 扩展与元数据
  `extra`             JSON,
  `schema_version`    VARCHAR(10)     DEFAULT 'v1.1'           COMMENT '模式版本',
  `compute_version`   VARCHAR(20),
  
  -- 强制三件套 (AGENTS.md 3.3)
  `created_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`            TINYINT(1) NOT NULL DEFAULT 0,
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_signal` (`user_id`, `trade_date`, `ts_code`, `pool_type`, `signal_type`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_is_deleted` (`is_deleted`),
  KEY `idx_trade_date` (`trade_date`),
  KEY `idx_ts_code` (`ts_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='A 股异动信号统一池';
