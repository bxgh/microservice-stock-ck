#!/usr/bin/env python3
"""
检查MySQL表结构脚本
"""
import asyncio
import aiomysql
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('/home/bxgh/microservice-stock/services/get-stockdata/.env')

async def check_mysql_table():
    """检查MySQL表结构"""
    try:
        # 连接MySQL
        conn = await aiomysql.connect(
            host=os.getenv('MYSQL_HOST'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            db=os.getenv('MYSQL_DATABASE'),
            charset='utf8mb4'
        )
        
        print("=" * 80)
        print("MySQL 连接成功！")
        print(f"服务器: {os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}")
        print(f"数据库: {os.getenv('MYSQL_DATABASE')}")
        print("=" * 80)
        
        async with conn.cursor() as cursor:
            # 1. 查看表结构
            print("\n【表结构】stock_kline_daily")
            print("-" * 80)
            await cursor.execute("DESC stock_kline_daily")
            rows = await cursor.fetchall()
            
            has_update_time = False
            has_create_time = False
            
            print(f"{'字段名':<25} {'类型':<20} {'允许NULL':<10} {'键':<10} {'默认值':<15}")
            print("-" * 80)
            for row in rows:
                field, type_, null, key, default, extra = row
                print(f"{field:<25} {type_:<20} {null:<10} {key:<10} {str(default):<15}")
                
                if field.lower() in ['update_time', 'updated_at', 'modify_time']:
                    has_update_time = True
                if field.lower() in ['create_time', 'created_at']:
                    has_create_time = True
            
            # 2. 查看数据量
            print("\n" + "=" * 80)
            print("【数据统计】")
            print("-" * 80)
            
            await cursor.execute("SELECT COUNT(*) as cnt FROM stock_kline_daily")
            total = (await cursor.fetchone())[0]
            print(f"总记录数: {total:,}")
            
            await cursor.execute("SELECT COUNT(DISTINCT stock_code) FROM stock_kline_daily")
            stock_count = (await cursor.fetchone())[0]
            print(f"股票数量: {stock_count:,}")
            
            await cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM stock_kline_daily")
            min_date, max_date = await cursor.fetchone()
            print(f"日期范围: {min_date} ~ {max_date}")
            
            # 3. 查看示例数据
            print("\n" + "=" * 80)
            print("【示例数据】(最新3条)")
            print("-" * 80)
            await cursor.execute("""
                SELECT stock_code, trade_date, open_price, close_price, volume
                FROM stock_kline_daily
                ORDER BY trade_date DESC
                LIMIT 3
            """)
            samples = await cursor.fetchall()
            for sample in samples:
                print(f"股票: {sample[0]}, 日期: {sample[1]}, 开盘: {sample[2]:.2f}, "
                      f"收盘: {sample[3]:.2f}, 成交量: {sample[4]:,}")
            
            # 4. 结论
            print("\n" + "=" * 80)
            print("【同步方案建议】")
            print("-" * 80)
            
            if has_update_time:
                print("✅ 表中有 update_time 字段")
                print("📌 推荐方案: 可以使用基于 update_time 的增量同步")
                print("   优势: 能捕获历史数据的修正和更新")
                print()
                
                # 检查update_time是否有索引
                await cursor.execute("SHOW INDEX FROM stock_kline_daily WHERE Column_name LIKE '%update%'")
                idx = await cursor.fetchall()
                if idx:
                    print("✅ update_time 已有索引，查询性能良好")
                else:
                    print("⚠️  update_time 无索引，建议添加:")
                    print("   CREATE INDEX idx_update_time ON stock_kline_daily(update_time);")
            else:
                print("❌ 表中无 update_time 字段")
                print("📌 推荐方案: 使用 --mode smart (基于最大日期)")
                print("   优势: 简单可靠，零依赖，性能好")
                print()
                
                if has_create_time:
                    print("ℹ️  表中有 create_time 字段（仅记录创建时间，无法追踪更新）")
                
                print("\n如需使用 update_time 方案，需要执行:")
                print("   ALTER TABLE stock_kline_daily")
                print("   ADD COLUMN update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                print("              ON UPDATE CURRENT_TIMESTAMP;")
        
        conn.close()
        print("\n" + "=" * 80)
        print("检查完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n可能的原因:")
        print("1. 网络连接问题（需要配置代理）")
        print("2. MySQL凭证错误")
        print("3. 数据库或表不存在")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_mysql_table())
