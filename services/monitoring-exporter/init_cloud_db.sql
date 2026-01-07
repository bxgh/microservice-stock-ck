-- Grafana Cloud 监控数据库初始化脚本
-- 在腾讯云 MySQL 上执行

-- 创建监控数据库
CREATE DATABASE IF NOT EXISTS monitoring 
DEFAULT CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE monitoring;

-- 系统指标表 (通用)
CREATE TABLE IF NOT EXISTS metrics_timeseries (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL COMMENT '指标名称',
    metric_value DOUBLE NOT NULL COMMENT '指标值',
    labels JSON COMMENT '标签 (JSON)',
    server VARCHAR(50) DEFAULT 'server41' COMMENT '服务器标识',
    timestamp DATETIME NOT NULL COMMENT '时间戳',
    INDEX idx_metric_time (metric_name, timestamp),
    INDEX idx_server_time (server, timestamp)
) ENGINE=InnoDB COMMENT='通用时序指标表';

-- ClickHouse 复制状态
CREATE TABLE IF NOT EXISTS clickhouse_replication (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    server VARCHAR(50) NOT NULL,
    database_name VARCHAR(100),
    table_name VARCHAR(100),
    is_readonly TINYINT DEFAULT 0,
    absolute_delay INT COMMENT '复制延迟(秒)',
    queue_size INT COMMENT '复制队列大小',
    timestamp DATETIME NOT NULL,
    INDEX idx_server_time (server, timestamp)
) ENGINE=InnoDB COMMENT='ClickHouse 复制状态';

-- Redis 状态
CREATE TABLE IF NOT EXISTS redis_status (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    used_memory_mb DOUBLE COMMENT '已用内存(MB)',
    max_memory_mb DOUBLE COMMENT '最大内存(MB)',
    memory_usage_percent DOUBLE COMMENT '内存使用率(%)',
    connected_clients INT COMMENT '连接客户端数',
    ops_per_sec INT COMMENT '每秒操作数',
    timestamp DATETIME NOT NULL,
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB COMMENT='Redis 状态';

-- GOST 隧道状态
CREATE TABLE IF NOT EXISTS gost_tunnel_status (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tunnel_name VARCHAR(50) NOT NULL COMMENT '隧道名称',
    is_healthy TINYINT DEFAULT 1 COMMENT '是否健康',
    reconnect_count INT DEFAULT 0 COMMENT '重连次数',
    last_check_time DATETIME COMMENT '最后检查时间',
    timestamp DATETIME NOT NULL,
    INDEX idx_tunnel_time (tunnel_name, timestamp)
) ENGINE=InnoDB COMMENT='GOST 隧道状态';

-- 系统资源使用
CREATE TABLE IF NOT EXISTS system_resources (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    server VARCHAR(50) NOT NULL,
    cpu_usage_percent DOUBLE COMMENT 'CPU 使用率(%)',
    memory_total_gb DOUBLE COMMENT '总内存(GB)',
    memory_used_gb DOUBLE COMMENT '已用内存(GB)',
    disk_total_gb DOUBLE COMMENT '总磁盘(GB)',
    disk_used_gb DOUBLE COMMENT '已用磁盘(GB)',
    timestamp DATETIME NOT NULL,
    INDEX idx_server_time (server, timestamp)
) ENGINE=InnoDB COMMENT='系统资源使用';

-- 创建只读用户供 Grafana Cloud 使用
CREATE USER IF NOT EXISTS 'grafana_readonly'@'%' IDENTIFIED BY 'alwaysup@monitoring';
GRANT SELECT ON monitoring.* TO 'grafana_readonly'@'%';
FLUSH PRIVILEGES;

-- 创建定时清理事件 (保留 30 天数据)
DELIMITER $$

CREATE EVENT IF NOT EXISTS cleanup_old_metrics
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
BEGIN
    DELETE FROM metrics_timeseries WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
    DELETE FROM clickhouse_replication WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
    DELETE FROM redis_status WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
    DELETE FROM gost_tunnel_status WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
    DELETE FROM system_resources WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
END$$

DELIMITER ;

-- 启用事件调度器
SET GLOBAL event_scheduler = ON;

-- 验证表创建
SHOW TABLES;

SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    ROUND(DATA_LENGTH / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'monitoring'
ORDER BY TABLE_NAME;
