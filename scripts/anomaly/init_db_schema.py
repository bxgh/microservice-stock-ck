import os
import pymysql
import sys
from dotenv import load_dotenv

def init_table(sql_file):
    load_dotenv()
    
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", 36301))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "alwaysup@888")
    db = os.getenv("MYSQL_DB", "alwaysup")
    
    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    try:
        with connection.cursor() as cursor:
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql = f.read()
                # Use a more robust split for statements
                # Note: This is still simple, but works for standard DDLs
                commands = sql.split(';')
                for command in commands:
                    if command.strip():
                        cursor.execute(command)
        connection.commit()
        print(f"✅ Table in {sql_file} initialized successfully.")
    except Exception as e:
        print(f"❌ Error initializing {sql_file}: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        init_table(sys.argv[1])
    else:
        print("Usage: python init_db_schema.py <sql_file>")
