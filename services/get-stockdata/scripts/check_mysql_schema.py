"""
查询MySQL表结构的脚本
"""
import asyncio
import aiomysql
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

async def check_mysql_schema():
    """查询MySQL表结构"""
    try:
        conn = await aiomysql.connect(
            host=os.getenv('MYSQL_HOST'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            db=os.getenv('MYSQL_DATABASE'),
            charset='utf8mb4'
        )
        
        async with conn.cursor() as cursor:
            # 查看表结构
            await cursor.execute("DESC stock_kline_daily")
            schema = await cursor.fetchall()
            
            print("=" * 80)
            print("MySQL 表结构: stock_kline_daily")
            print("=" * 80)
            for row in schema:
                print(f"{row[0]:<20} {row[1]:<20} {row[2]:<10} {row[3]:<10}")
            
            # 查看数据量
            await cursor.execute("SELECT COUNT(*) FROM stock_kline_daily")
            count = await cursor.fetchone()
            print(f"\n总记录数: {count[0]:,}")
            
            # 查看股票代码数量
            await cursor.execute("SELECT COUNT(DISTINCT stock_code) FROM stock_kline_daily")
            stock_count = await cursor.fetchone()
            print(f"股票数量: {stock_count[0]:,}")
            
            # 查看日期范围
            await cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM stock_kline_daily")
            date_range = await cursor.fetchone()
            print(f"日期范围: {date_range[0]} ~ {date_range[1]}")
            
            # 查看示例数据
            await cursor.execute("SELECT * FROM stock_kline_daily LIMIT 3")
            samples = await cursor.fetchall()
            print("\n示例数据:")
            for sample in samples:
                print(sample)
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    asyncio.run(check_mysql_schema())
