CREATE TABLE IF NOT EXISTS `alwaysup`.`task_commands` (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL COMMENT '任务ID，如 pre_market_gate',
    params JSON COMMENT '可选参数，如 {"target_date": "20260113"}',
    status ENUM('PENDING', 'RUNNING', 'DONE', 'FAILED') DEFAULT 'PENDING',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    executed_at DATETIME,
    result TEXT COMMENT '执行结果或错误信息',
    INDEX idx_status (status)
) COMMENT='异步任务命令队列';
