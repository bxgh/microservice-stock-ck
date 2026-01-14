import pymysql
import sys

def update_db():
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            port=36301,
            user='root',
            password='alwaysup@888',
            database='monitoring',
            charset='utf8mb4',
            autocommit=True
        )
        with conn.cursor() as cursor:
            # 检查字段是否已存在，防止重复执行报错
            cursor.execute("SHOW COLUMNS FROM clickhouse_business_metrics LIKE 'tick_today'")
            if not cursor.fetchone():
                print("Adding missing columns to clickhouse_business_metrics...")
                alter_query = """
                ALTER TABLE clickhouse_business_metrics 
                ADD COLUMN tick_today INT DEFAULT 0 COMMENT '今日分笔股票数',
                ADD COLUMN tick_expected INT DEFAULT 5000 COMMENT '预期分笔股票数',
                ADD COLUMN kline_coverage_rate DECIMAL(5,2) DEFAULT 0 COMMENT 'K线覆盖率%',
                ADD COLUMN tick_coverage_rate DECIMAL(5,2) DEFAULT 0 COMMENT '分笔覆盖率%',
                ADD COLUMN hs300_kline INT DEFAULT 0 COMMENT '沪深300 K线覆盖数',
                ADD COLUMN hs300_tick INT DEFAULT 0 COMMENT '沪深300分笔覆盖数';
                """
                cursor.execute(alter_query)
                print("✅ Database schema updated successfully.")
            else:
                print("ℹ️ Columns already exist, skipping update.")
                
        # 创建任务失败告警表
        with conn.cursor() as cursor:
            print("Creating task_execution_alerts table...")
            create_table_query = """
            CREATE TABLE IF NOT EXISTS task_execution_alerts (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                task_id VARCHAR(100),
                task_name VARCHAR(100),
                status ENUM('FAILED', 'TIMEOUT', 'MISSED'),
                error_message TEXT,
                detected_at DATETIME,
                notified TINYINT DEFAULT 0,
                INDEX idx_status_time (status, detected_at)
            ) ENGINE=InnoDB COMMENT='任务执行告警记录';
            """
            cursor.execute(create_table_query)
            print("✅ task_execution_alerts table ensured.")
            
        conn.close()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    update_db()
