-- ============================================
-- 任务 ID: [E1-S3-T1]
-- 描述: 创建标签字典与关系表
-- 规范: MySQL 5.7, 包含软删除与更新时间索引
-- ============================================

CREATE TABLE IF NOT EXISTS `dim_tag_dictionary` (
  `tag_code`         VARCHAR(40)  NOT NULL COMMENT '标签编码',
  `tag_name_cn`      VARCHAR(50)  NOT NULL COMMENT '标签中文名',
  `tag_category`     VARCHAR(20)  NOT NULL COMMENT '标签大类',
  `tag_subcategory`  VARCHAR(20)           COMMENT '标签小类',
  `tag_description`  VARCHAR(200)          COMMENT '标签描述',
  `display_order`    INT          DEFAULT 100 COMMENT '显示顺序',
  `is_active`        TINYINT(1)   DEFAULT 1   COMMENT '是否启用',
  `tag_meta`         JSON                  COMMENT '元数据配置',
  
  -- 强制三件套 (AGENTS.md 3.3)
  `created_at`       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`       TINYINT(1) NOT NULL DEFAULT 0,
  
  PRIMARY KEY (`tag_code`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='异动标签字典表';

CREATE TABLE IF NOT EXISTS `dim_tag_relation` (
  `tag_a`            VARCHAR(40)  NOT NULL COMMENT '源标签',
  `tag_b`            VARCHAR(40)  NOT NULL COMMENT '目标标签',
  `relation_type`    VARCHAR(20)  NOT NULL COMMENT '关系类型 (mutex/imply/correlate)',
  
  -- 强制三件套 (AGENTS.md 3.3)
  `created_at`       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`       TINYINT(1) NOT NULL DEFAULT 0,
  
  PRIMARY KEY (`tag_a`, `tag_b`, `relation_type`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='标签逻辑关系表';
