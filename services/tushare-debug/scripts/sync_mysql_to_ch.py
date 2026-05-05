import pymysql
import clickhouse_driver
import os

def sync():
    db_args = dict(
        host=os.getenv("GSD_DB_HOST", "127.0.0.1"),
        port=int(os.getenv("GSD_DB_PORT", "36301")),
        user=os.getenv("GSD_DB_USER", "root"),
        password=os.getenv("GSD_DB_PASSWORD", "alwaysup@888"),
        database=os.getenv("GSD_DB_NAME", "alwaysup")
    )
    ch_args = dict(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
        user=os.getenv("CLICKHOUSE_USER", "admin"),
        password=os.getenv("CLICKHOUSE_PASSWORD", "admin123"),
        database=os.getenv("CLICKHOUSE_DB", "stock_data")
    )

    mysql_conn = pymysql.connect(**db_args)
    ch_client = clickhouse_driver.Client(**ch_args)

    try:
        with mysql_conn.cursor() as cursor:
            # 分页分批同步
            offset = 0
            limit = 50000
            total_synced = 0
            
            while True:
                sql = f"SELECT ts_code, trade_date, turnover_rate, pe, pb, ps, total_mv, circ_mv, close FROM daily_basic WHERE trade_date >= '2025-08-01' LIMIT {offset}, {limit}"
                print(f"Fetching batch: {offset} to {offset + limit}...")
                cursor.execute(sql)
                rows = cursor.fetchall()
                if not rows:
                    break
                
                data = [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]) for r in rows]
                ch_client.execute("INSERT INTO stock_valuation (stock_code, trade_date, turnover_rate, pe, pb, ps, market_cap, circ_mv, price) VALUES", data)
                
                total_synced += len(rows)
                offset += limit
                print(f"Synced {total_synced} records...")

            print(f"✅ Sync complete! Total: {total_synced}")

    finally:
        mysql_conn.close()

if __name__ == "__main__":
    sync()
