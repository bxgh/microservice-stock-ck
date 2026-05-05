-- 监控扩展表结构 (在腾讯云 MySQL monitoring 库中执行)
-- 版本: 1.1
-- 日期: 2026-01-06

USE monitoring;

-- 微服务健康状态表
CREATE TABLE IF NOT EXISTS service_health (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL COMMENT '服务名称',
    is_healthy TINYINT DEFAULT 1 COMMENT '是否健康 (1=是, 0=否)',
    response_time_ms DOUBLE COMMENT '响应时间(毫秒), -1表示无响应',
    timestamp DATETIME NOT NULL COMMENT '检查时间',
    INDEX idx_service_time (service_name, timestamp),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB COMMENT='微服务健康状态';

-- Docker 容器状态表
CREATE TABLE IF NOT EXISTS docker_status (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    server VARCHAR(50) NOT NULL COMMENT '服务器标识',
    container_name VARCHAR(100) NOT NULL COMMENT '容器名称',
    status VARCHAR(100) COMMENT '状态描述',
    image VARCHAR(100) COMMENT '镜像名称',
    is_running TINYINT DEFAULT 0 COMMENT '是否运行中',
    timestamp DATETIME NOT NULL COMMENT '采集时间',
    INDEX idx_server_time (server, timestamp),
    INDEX idx_container_time (container_name, timestamp)
) ENGINE=InnoDB COMMENT='Docker 容器状态';

-- ClickHouse 业务指标表
CREATE TABLE IF NOT EXISTS clickhouse_business_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    kline_today BIGINT DEFAULT 0 COMMENT '今日K线同步条数',
    kline_total BIGINT DEFAULT 0 COMMENT 'K线总条数',
    snapshot_today BIGINT DEFAULT 0 COMMENT '今日快照数据量',
    stock_count INT DEFAULT 0 COMMENT '近7天股票覆盖数',
    timestamp DATETIME NOT NULL COMMENT '采集时间',
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB COMMENT='ClickHouse 业务指标';

-- 更新清理事件，加入新表
DROP EVENT IF EXISTS cleanup_old_metrics;

DELIMITER $$

CREATE EVENT cleanup_old_metrics
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
BEGIN
    DELETE FROM metrics_timeseries WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
    DELETE FROM clickhouse_replication WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
    DELETE FROM redis_status WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
    DELETE FROM gost_tunnel_status WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
    DELETE FROM system_resources WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
    DELETE FROM service_health WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
    DELETE FROM docker_status WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
    DELETE FROM clickhouse_business_metrics WHERE timestamp < DATE_SUB(NOW(), INTERVAL 30 DAY);
END$$

DELIMITER ;

-- 验证表创建
SHOW TABLES;
