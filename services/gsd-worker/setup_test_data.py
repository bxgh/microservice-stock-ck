#!/usr/bin/env python3
"""
准备测试数据并运行功能测试
"""

import pymysql
from datetime import datetime, timedelta

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 36301,
    'user': 'root',
    'password': 'alwaysup@888',
    'database': 'alwaysup',
    'charset': 'utf8mb4'
}

def setup_test_data():
    """准备测试数据"""
    print("=" * 80)
    print("准备测试数据")
    print("=" * 80)
    
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 1. 清理旧的测试数据
        print("\n[步骤1] 清理旧的测试数据...")
        cursor.execute("""
            DELETE FROM sync_progress 
            WHERE task_name = 'full_market_sync' 
              AND DATE(updated_at) >= DATE_SUB(CURDATE(), INTERVAL 2 DAY)
        """)
        deleted = cursor.rowcount
        print(f"✓ 删除了 {deleted} 条旧记录")
        
        # 2. 更新为"昨日"历史记录
        print("\n[步骤2] 更新昨日历史记录（用于历史预测）...")
        yesterday_time = datetime.now() - timedelta(days=1)
        yesterday_time = yesterday_time.replace(hour=18, minute=55, second=0, microsecond=0)
        
        cursor.execute("""
            UPDATE sync_progress 
            SET status = %s, total_count = %s, updated_at = %s
            WHERE task_name = %s
        """, ('completed', 5000, yesterday_time, 'full_market_sync'))
        print(f"✓ 更新昨日记录: {yesterday_time.strftime('%Y-%m-%d %H:%M:%S')}, 5000条")
        
        # 3. 插入"今日"完成记录（使用不同的task_name避免冲突）
        print("\n[步骤3] 插入今日测试记录（用于信号检测）...")
        today_time = datetime.now()
        
        # 先删除可能存在的今日测试记录
        cursor.execute("DELETE FROM sync_progress WHERE task_name = 'full_market_sync_test'")
        
        cursor.execute("""
            INSERT INTO sync_progress (task_name, status, total_count, updated_at)
            VALUES (%s, %s, %s, %s)
        """, ('full_market_sync_test', 'completed', 5100, today_time))
        print(f"✓ 插入今日记录: {today_time.strftime('%Y-%m-%d %H:%M:%S')}, 5100条")
        
        conn.commit()
        
        # 4. 验证插入结果
        print("\n[步骤4] 验证插入结果...")
        cursor.execute("""
            SELECT 
                task_name,
                status,
                total_count,
                updated_at,
                CASE 
                    WHEN DATE(updated_at) = CURDATE() THEN '今日'
                    WHEN DATE(updated_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY) THEN '昨日'
                    ELSE '其他'
                END AS date_label
            FROM sync_progress 
            WHERE task_name = 'full_market_sync'
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        
        print("\n最近的记录:")
        print(f"{'任务名称':<25} {'状态':<10} {'记录数':<10} {'时间':<20} {'标签':<10}")
        print("-" * 80)
        
        for row in cursor.fetchall():
            task_name, status, total_records, updated_at, date_label = row
            print(f"{task_name:<25} {status:<10} {total_records:<10} {str(updated_at):<20} {date_label:<10}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        print("✅ 测试数据准备完成！")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = setup_test_data()
    exit(0 if success else 1)
