-- 巡检模块数据库表结构
-- 创建时间: 2026-05-04

-- 1. dq_findings: 记录具体的异常点 (例如：某股票某日缺失)
CREATE TABLE IF NOT EXISTS alwaysup.dq_findings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(12) NOT NULL COMMENT '股票代码',
    trade_date DATE NOT NULL COMMENT '发生日期',
    rule_id VARCHAR(50) NOT NULL COMMENT '规则ID (integrity/continuity/suspension)',
    severity VARCHAR(10) DEFAULT 'WARN' COMMENT '严重等级 (INFO/WARN/ERROR)',
    description TEXT COMMENT '异常详细描述',
    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '发现时间',
    status VARCHAR(20) DEFAULT 'OPEN' COMMENT '状态 (OPEN/FIXED/IGNORED)',
    INDEX idx_date (trade_date),
    INDEX idx_code (ts_code),
    INDEX idx_rule (rule_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. dq_reports: 记录每次巡检的汇总信息
CREATE TABLE IF NOT EXISTS alwaysup.dq_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inspection_date DATE NOT NULL COMMENT '巡检目标日期',
    start_time TIMESTAMP NOT NULL COMMENT '开始时间',
    end_time TIMESTAMP NULL COMMENT '结束时间',
    score DECIMAL(5,2) DEFAULT 0.00 COMMENT '数据质量得分',
    summary JSON COMMENT '汇总数据 (各类异常统计)',
    status VARCHAR(20) DEFAULT 'COMPLETED' COMMENT '执行状态',
    UNIQUE INDEX idx_inspection_date (inspection_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
