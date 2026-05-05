
import pymysql
import os

def create_table():
    host = '127.0.0.1'
    port = 36301
    user = os.getenv('GSD_DB_USER', 'root')
    password = os.getenv('GSD_DB_PASSWORD', 'dev_password')
    db = os.getenv('GSD_DB_NAME', 'stock_data')
    
    print(f"Connecting to MySQL ({host}:{port})...")
    conn = pymysql.connect(host=host, port=port, user=user, password=password, db=db)
    
    table_sql = """
    CREATE TABLE IF NOT EXISTS sync_execution_logs (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        task_name VARCHAR(50) NOT NULL COMMENT '任务名称',
        execution_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
        status VARCHAR(20) NOT NULL COMMENT '状态: SUCCESS, FAILED, RUNNING',
        records_processed INT DEFAULT 0 COMMENT '同步/处理记录数',
        details TEXT COMMENT '详细日志信息',
        duration_seconds FLOAT DEFAULT 0.0 COMMENT '耗时(秒)',
        INDEX idx_task_time (task_name, execution_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='本地任务执行日志表';
    """
    
    try:
        with conn.cursor() as cursor:
            print("Creating table 'sync_execution_logs'...")
            cursor.execute(table_sql)
            print("Table created successfully.")
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_table()
