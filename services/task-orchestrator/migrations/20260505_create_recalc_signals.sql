-- E6 重算信号管理表
-- 创建时间: 2026-05-05

CREATE TABLE IF NOT EXISTS alwaysup.recalc_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id VARCHAR(50) NOT NULL COMMENT '外部请求ID (BF-日期-序列号)',
    ts_code VARCHAR(12) NOT NULL COMMENT '股票代码',
    start_date DATE NOT NULL COMMENT '重算起始日期',
    end_date DATE NOT NULL COMMENT '重算结束日期',
    status VARCHAR(20) DEFAULT 'PENDING' COMMENT '状态 (PENDING/PROCESSING/COMPLETED/FAILED)',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    notes TEXT COMMENT '执行备注或错误信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    executed_at TIMESTAMP NULL COMMENT '节点领取任务时间',
    UNIQUE INDEX idx_request_id (request_id),
    INDEX idx_status (status),
    INDEX idx_ts_code (ts_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
