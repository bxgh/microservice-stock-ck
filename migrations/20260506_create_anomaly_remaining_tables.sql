-- ============================================
-- 任务 ID: [E1-S4 到 E1-S8]
-- 描述: 创建异动捕捉模块剩余维度表与应用表
-- 规范: MySQL 5.7, 包含软删除与更新时间索引
-- ============================================

-- E1-S4: 筛选模板表
CREATE TABLE IF NOT EXISTS `dim_filter_profile` (
  `profile_code`     VARCHAR(40)  NOT NULL COMMENT '模板编码',
  `profile_name`     VARCHAR(50)  NOT NULL COMMENT '模板名称',
  `rules_json`       JSON         NOT NULL COMMENT '规则配置',
  `is_system`        TINYINT(1)   DEFAULT 1 COMMENT '是否系统预设',
  
  -- 强制三件套
  `created_at`       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`       TINYINT(1) NOT NULL DEFAULT 0,
  
  PRIMARY KEY (`profile_code`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='异动筛选模板表';

-- E1-S5: 市场状态表
CREATE TABLE IF NOT EXISTS `ads_market_state_daily` (
  `trade_date`           DATE         NOT NULL COMMENT '交易日',
  `is_normal`            TINYINT(1)   DEFAULT 1 COMMENT '是否正常交易',
  `abnormal_reasons`     JSON                  COMMENT '异常理由',
  `signal_reliability`   DECIMAL(4,2) DEFAULT 1.00 COMMENT '信号可信度系数',
  
  -- 强制三件套
  `created_at`           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`           TINYINT(1) NOT NULL DEFAULT 0,
  
  PRIMARY KEY (`trade_date`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='每日市场状态与信号可信度';

-- E1-S6: Top 10 推送清单表
CREATE TABLE IF NOT EXISTS `app_anomaly_top10_daily` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`           BIGINT UNSIGNED NOT NULL DEFAULT 1,
  `trade_date`        DATE            NOT NULL,
  `rank_no`           TINYINT         NOT NULL COMMENT '排名(1-10)',
  `signal_id`         BIGINT UNSIGNED NOT NULL COMMENT '关联统一信号表ID',
  `ts_code`           VARCHAR(20)     NOT NULL,
  `name`              VARCHAR(50)     NOT NULL,
  `pool_type`         VARCHAR(16)     NOT NULL COMMENT '所属池子',
  `composite_score`   DECIMAL(6,2)    NOT NULL COMMENT '综合得分',
  `quota_slot`        VARCHAR(20)     NOT NULL COMMENT '占用配额位',
  `profile_code`      VARCHAR(40)              COMMENT '关联模板',
  `headline`          VARCHAR(200)             COMMENT '中文标题',
  `key_features`      JSON                     COMMENT '关键特征快照',
  
  -- 强制三件套
  `created_at`        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`        TINYINT(1) NOT NULL DEFAULT 0,
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_date_rank` (`user_id`, `trade_date`, `rank_no`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_is_deleted` (`is_deleted`),
  KEY `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='异动 Top 10 推送表';

-- E1-S7: 评分权重配置表
CREATE TABLE IF NOT EXISTS `dim_anomaly_score_weight` (
  `version`           VARCHAR(20)  NOT NULL COMMENT '版本号',
  `weight_key`        VARCHAR(40)  NOT NULL COMMENT '权重项标识',
  `weight_value`      DECIMAL(6,4) NOT NULL COMMENT '权重值',
  `is_active`         TINYINT(1)   DEFAULT 0 COMMENT '是否启用',
  
  -- 强制三件套
  `created_at`        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`        TINYINT(1) NOT NULL DEFAULT 0,
  
  PRIMARY KEY (`version`, `weight_key`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='评分权重配置表';

-- E1-S8: 用户板块偏好表
CREATE TABLE IF NOT EXISTS `dim_user_sector_pref` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`           BIGINT UNSIGNED NOT NULL DEFAULT 1,
  `sector_type`       VARCHAR(16)     NOT NULL COMMENT '板块类型(sw1/sw2/concept)',
  `sector_code`       VARCHAR(50)     NOT NULL,
  `sector_name`       VARCHAR(50)     NOT NULL,
  `weight`            DECIMAL(4,2)    NOT NULL DEFAULT 1.00 COMMENT '加权系数',
  `is_active`         TINYINT(1)      NOT NULL DEFAULT 1,
  
  -- 强制三件套
  `created_at`        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`        TINYINT(1) NOT NULL DEFAULT 0,
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_sector` (`user_id`, `sector_type`, `sector_code`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='用户板块偏好加权配置';
