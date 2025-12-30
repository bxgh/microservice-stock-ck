#!/usr/bin/env python3
"""
使用pymysql同步连接检查MySQL表结构
"""
import pymysql
import sys

# MySQL连接配置
config = {
    'host': 'sh-cdb-h7flpxu4.sql.tencentcdb.com',
    'port': 26300,
    'user': 'root',
    'password': 'alwaysup@888',
    'database': 'alwaysup',
    'charset': 'utf8mb4',
    'connect_timeout': 10
}

try:
    print("正在连接MySQL...")
    print(f"服务器: {config['host']}:{config['port']}")
    print(f"数据库: {config['database']}")
    print("=" * 80)
    
    # 连接MySQL
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    # 查看表结构
    print("\n【表结构】stock_kline_daily")
    print("-" * 80)
    cursor.execute("DESC stock_kline_daily")
    
    print(f"{'字段名':<25} {'类型':<20} {'允许NULL':<10} {'键':<10}")
    print("-" * 80)
    
    has_created_at = False
    has_update_time = False
    
    for row in cursor.fetchall():
        field, type_, null, key, default, extra = row
        print(f"{field:<25} {type_:<20} {null:<10} {key:<10}")
        
        if field.lower() in ['created_at', 'create_time', 'createtime']:
            has_created_at = True
        if field.lower() in ['updated_at', 'update_time', 'updatetime']:
            has_update_time = True
    
    # 统计信息
    print("\n" + "=" * 80)
    print("【数据统计】")
    print("-" * 80)
    
    cursor.execute("SELECT COUNT(*) FROM stock_kline_daily")
    total = cursor.fetchone()[0]
    print(f"总记录数: {total:,}")
    
    cursor.execute("SELECT COUNT(DISTINCT stock_code) FROM stock_kline_daily")
    stock_count = cursor.fetchone()[0]
    print(f"股票数量: {stock_count}")
    
    cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM stock_kline_daily")
    min_date, max_date = cursor.fetchone()
    print(f"日期范围: {min_date} ~ {max_date}")
    
    # 建议
    print("\n" + "=" * 80)
    print("【同步方案推荐】")
    print("-" * 80)
    
    if has_created_at:
        print("✅ 表中有 created_at 字段")
        print("📌 推荐使用: --mode created_at --hours 48")
        print("   优势: 精确到秒级，能处理分批写入")
    elif has_update_time:
        print("✅ 表中有 update_time 字段")
        print("📌 可以基于 update_time 实现增量同步（需要额外开发）")
    else:
        print("❌ 表中无时间戳字段")
        print("📌 推荐使用: --mode smart")
        print("   优势: 基于最大日期，简单可靠")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 检查完成！")
    print("=" * 80)
    
except pymysql.err.OperationalError as e:
    print(f"\n❌ 连接失败: {e}")
    print("\n可能的原因:")
    print("1. 网络无法访问腾讯云（需要代理）")
    print("2. IP白名单限制")
    print("3. 防火墙拦截")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
