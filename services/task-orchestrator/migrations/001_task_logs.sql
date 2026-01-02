-- Task Orchestrator 任务执行日志表
-- 版本: 001
-- 日期: 2026-01-02

CREATE TABLE IF NOT EXISTS task_execution_logs (
    -- 主键
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 任务标识
    task_id VARCHAR(100) NOT NULL COMMENT '任务ID (来自YAML配置)',
    task_name VARCHAR(200) NOT NULL COMMENT '任务名称',
    
    -- 执行状态
    status ENUM('RUNNING', 'SUCCESS', 'FAILED', 'TIMEOUT', 'CANCELLED') NOT NULL COMMENT '执行状态',
    
    -- 时间信息
    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME DEFAULT NULL COMMENT '结束时间',
    duration_seconds INT DEFAULT NULL COMMENT '执行耗时(秒)',
    
    -- 执行结果
    exit_code INT DEFAULT NULL COMMENT '退出码 (0=成功)',
    error_message TEXT DEFAULT NULL COMMENT '错误信息',
    
    -- 容器信息 (仅Docker任务)
    container_id VARCHAR(100) DEFAULT NULL COMMENT 'Docker容器ID',
    
    -- 扩展信息
    metadata JSON DEFAULT NULL COMMENT '元数据 (JSON格式)',
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    
    -- 索引
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务执行日志';

-- 创建统计视图 (可选)
CREATE OR REPLACE VIEW task_execution_stats AS
SELECT 
    task_id,
    task_name,
    COUNT(*) as total_executions,
    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
    ROUND(
        SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*) * 100, 
        2
    ) as success_rate,
    AVG(duration_seconds) as avg_duration_seconds,
    MAX(start_time) as last_run_time
FROM task_execution_logs
GROUP BY task_id, task_name;
