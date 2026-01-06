#!/usr/bin/env python3
"""
执行监控表扩展 DDL
在腾讯云 MySQL (通过 GOST 隧道) 创建新的监控表
"""

import pymysql

# 连接配置
config = {
    'host': '127.0.0.1',
    'port': 36301,
    'user': 'root',
    'password': 'alwaysup@888',
    'database': 'monitoring',
    'charset': 'utf8mb4',
    'autocommit': True
}

# DDL 语句
ddl_statements = [
    """
    CREATE TABLE IF NOT EXISTS service_health (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        service_name VARCHAR(50) NOT NULL COMMENT '服务名称',
        is_healthy TINYINT DEFAULT 1 COMMENT '是否健康 (1=是, 0=否)',
        response_time_ms DOUBLE COMMENT '响应时间(毫秒), -1表示无响应',
        timestamp DATETIME NOT NULL COMMENT '检查时间',
        INDEX idx_service_time (service_name, timestamp),
        INDEX idx_timestamp (timestamp)
    ) ENGINE=InnoDB COMMENT='微服务健康状态'
    """,
    """
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
    ) ENGINE=InnoDB COMMENT='Docker 容器状态'
    """,
    """
    CREATE TABLE IF NOT EXISTS clickhouse_business_metrics (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        kline_today BIGINT DEFAULT 0 COMMENT '今日K线同步条数',
        kline_total BIGINT DEFAULT 0 COMMENT 'K线总条数',
        snapshot_today BIGINT DEFAULT 0 COMMENT '今日快照数据量',
        stock_count INT DEFAULT 0 COMMENT '近7天股票覆盖数',
        timestamp DATETIME NOT NULL COMMENT '采集时间',
        INDEX idx_timestamp (timestamp)
    ) ENGINE=InnoDB COMMENT='ClickHouse 业务指标'
    """
]

def main():
    print("=" * 50)
    print("📊 开始创建监控扩展表...")
    print("=" * 50)
    
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        for i, ddl in enumerate(ddl_statements, 1):
            try:
                cursor.execute(ddl)
                table_name = ddl.split('CREATE TABLE IF NOT EXISTS ')[1].split(' (')[0]
                print(f"✅ [{i}/{len(ddl_statements)}] 创建表 {table_name} 成功")
            except Exception as e:
                print(f"❌ [{i}/{len(ddl_statements)}] 执行失败: {e}")
        
        # 验证
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("\n📋 当前表列表:")
        for t in tables:
            print(f"   - {t[0]}")
        
        cursor.close()
        conn.close()
        print("\n✅ 监控表创建完成！")
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        raise

if __name__ == "__main__":
    main()
