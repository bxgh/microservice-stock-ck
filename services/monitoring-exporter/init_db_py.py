import pymysql
import sys

def init_db():
    try:
        connection = pymysql.connect(
            host='127.0.0.1',
            port=36301,
            user='root',
            password='alwaysup@888',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Create database
            cursor.execute("CREATE DATABASE IF NOT EXISTS monitoring DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute("USE monitoring")
            
            # Create tables
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics_timeseries (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                metric_name VARCHAR(100) NOT NULL,
                metric_value DOUBLE NOT NULL,
                labels JSON,
                server VARCHAR(50) DEFAULT 'server41',
                timestamp DATETIME NOT NULL,
                INDEX idx_metric_time (metric_name, timestamp),
                INDEX idx_server_time (server, timestamp)
            ) ENGINE=InnoDB
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS clickhouse_replication (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                server VARCHAR(50) NOT NULL,
                database_name VARCHAR(100),
                table_name VARCHAR(100),
                is_readonly TINYINT DEFAULT 0,
                absolute_delay INT,
                queue_size INT,
                timestamp DATETIME NOT NULL,
                INDEX idx_server_time (server, timestamp)
            ) ENGINE=InnoDB
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS redis_status (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                used_memory_mb DOUBLE,
                max_memory_mb DOUBLE,
                memory_usage_percent DOUBLE,
                connected_clients INT,
                ops_per_sec INT,
                timestamp DATETIME NOT NULL,
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS gost_tunnel_status (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                tunnel_name VARCHAR(50) NOT NULL,
                is_healthy TINYINT DEFAULT 1,
                reconnect_count INT DEFAULT 0,
                last_check_time DATETIME,
                timestamp DATETIME NOT NULL,
                INDEX idx_tunnel_time (tunnel_name, timestamp)
            ) ENGINE=InnoDB
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_resources (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                server VARCHAR(50) NOT NULL,
                cpu_usage_percent DOUBLE,
                memory_total_gb DOUBLE,
                memory_used_gb DOUBLE,
                disk_total_gb DOUBLE,
                disk_used_gb DOUBLE,
                timestamp DATETIME NOT NULL,
                INDEX idx_server_time (server, timestamp)
            ) ENGINE=InnoDB
            """)
            
            # Create readonly user for Grafana
            try:
                cursor.execute("CREATE USER 'grafana_readonly'@'%' IDENTIFIED BY 'alwaysup@monitoring'")
                cursor.execute("GRANT SELECT ON monitoring.* TO 'grafana_readonly'@'%'")
            except Exception as e:
                print(f"User might already exist: {e}")
            
            cursor.execute("FLUSH PRIVILEGES")
            
        connection.commit()
        print("Database initialization successful!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    init_db()
