-- ============================================
-- 任务 ID: [E1-S1-T1]
-- 描述: 创建派生指标层表 ads_stock_derived_metrics
-- 规范: MySQL 5.7, 包含软删除与更新时间索引
-- ============================================

CREATE TABLE IF NOT EXISTS `ads_stock_derived_metrics` (
  `trade_date`            DATE         NOT NULL                  COMMENT '交易日',
  `ts_code`               VARCHAR(20)  NOT NULL                  COMMENT '股票代码',
  
  -- 量能派生
  `volume_ratio_5d`       DECIMAL(10,4)                          COMMENT '5 日量比均值',
  `volume_ratio_20d`      DECIMAL(10,4)                          COMMENT '20 日量比均值',
  `vol_5d_to_60d`         DECIMAL(10,4)                          COMMENT '5 日均量 / 60 日均量',
  `vol_consistency_days`  TINYINT                                COMMENT '连续满足量比 ∈ [1.5,2.5] 的天数',
  
  -- 涨跌幅派生
  `cumulative_5d_pct`     DECIMAL(10,6)                          COMMENT '5 日累计涨跌幅',
  `cumulative_20d_pct`    DECIMAL(10,6)                          COMMENT '20 日累计涨跌幅',
  `cumulative_60d_pct`    DECIMAL(10,6)                          COMMENT '60 日累计涨跌幅',
  `amplitude_today`       DECIMAL(10,6)                          COMMENT '当日振幅',
  `amplitude_10d`         DECIMAL(10,6)                          COMMENT '10 日总振幅',
  
  -- 排名派生
  `industry_rank_pct_today`    DECIMAL(6,4)                      COMMENT '行业内涨幅分位(0=最强)',
  `industry_rank_pct_avg_5d`   DECIMAL(6,4)                      COMMENT '前 5 日行业内分位均值',
  `capital_rank_today`         INT                               COMMENT '主力净流入全市场排名',
  `capital_rank_avg_5d`        DECIMAL(8,2)                      COMMENT '前 5 日主力排名均值',
  
  -- 均线派生
  `dist_to_ma5`           DECIMAL(10,6)                          COMMENT '与 MA5 的乖离率',
  `dist_to_ma10`          DECIMAL(10,6)                          COMMENT '与 MA10 的乖离率',
  `dist_to_ma20`          DECIMAL(10,6)                          COMMENT '与 MA20 的乖离率',
  `dist_to_ma60`          DECIMAL(10,6)                          COMMENT '与 MA60 的乖离率',
  `dist_to_ma250`         DECIMAL(10,6)                          COMMENT '与 MA250 的乖离率',
  `ma_convergence`        DECIMAL(10,6)                          COMMENT '均线粘合度',
  
  -- 形态派生
  `box_test_count_60d`    TINYINT                                COMMENT '60 日内压力位测试次数',
  `box_resistance_level`  DECIMAL(16,4)                          COMMENT '识别出的压力位价格',
  `is_first_recovery_ma250` TINYINT(1)                           COMMENT '是否首次站稳 MA250',
  
  -- 扩展与元数据
  `extra_metrics`         JSON                                   COMMENT '扩展指标JSON',
  `schema_version`        VARCHAR(10)  DEFAULT 'v1.1'           COMMENT '模式版本',
  
  -- 强制三件套 (AGENTS.md 3.3)
  `created_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`            TINYINT(1) NOT NULL DEFAULT 0,
  
  PRIMARY KEY (`trade_date`, `ts_code`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='A 股派生指标层';
