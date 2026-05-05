import pymysql

def list_tables():
    conn = pymysql.connect(
        host='127.0.0.1',
        port=36301,
        user='root',
        password='alwaysup@888',
        database='alwaysup'
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print("Tables in alwaysup:", tables)
            
            for (table_name,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"Table: {table_name}, Row Count: {count}")
    finally:
        conn.close()

if __name__ == "__main__":
    list_tables()
