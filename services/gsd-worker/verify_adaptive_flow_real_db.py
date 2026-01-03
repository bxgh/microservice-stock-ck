#!/usr/bin/env python3
"""
验证自适应调度器的完整工作流程模拟
模拟场景: 
1. 初始状态为"昨日完成"，调度器进入等待/轮询
2. 更新状态为"今日完成"，调度器应检测到信号并完成
"""

import sys
import asyncio
import pymysql
import logging
from datetime import datetime, timedelta
from pathlib import Path
import os

# Config logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VerifyFlow")

# 添加src路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from core.adaptive_scheduler import AdaptiveKLineSyncScheduler, CloudSyncException

# DB Config
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 36301,
    'user': 'root',
    'password': 'alwaysup@888',
    'database': 'alwaysup',
    'charset': 'utf8mb4',
    'autocommit': True
}

class MockPool:
    """简单的Mock连接池，包装pymysql连接"""
    def __init__(self):
        pass
        
    def acquire(self):
        return MockConnectionContext()

class MockConnectionContext:
    async def __aenter__(self):
        self.conn = await self._connect()
        return self.conn
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
            
    async def _connect(self):
        # 使用aiomysql真实连接
        import aiomysql
        conn = await aiomysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            db=DB_CONFIG['database']
        )
        return conn

def update_db_to_yesterday():
    """将数据库状态重置为'昨日完成'"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 确保记录存在
    cursor.execute("SELECT * FROM sync_progress WHERE task_name='full_market_sync'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO sync_progress (task_name, status, total_count, updated_at) VALUES (%s, %s, %s, %s)",
            ('full_market_sync', 'completed', 5000, datetime.now())
        )
    
    # 更新为昨日
    yesterday = datetime.now() - timedelta(days=1)
    yesterday = yesterday.replace(hour=18, minute=55, second=0) # 假设昨日18:55完成
    
    cursor.execute("""
        UPDATE sync_progress 
        SET status='completed', total_count=5000, updated_at=%s 
        WHERE task_name='full_market_sync'
    """, (yesterday,))
    
    # 还要删除可能存在的今日测试记录(避免干扰)
    cursor.execute("DELETE FROM sync_progress WHERE task_name='full_market_sync_test'")
    
    conn.close()
    logger.info(f"💾 DB状态已重置: full_market_sync = 昨日 ({yesterday})")

def update_db_to_today():
    """将数据库状态更新为'今日完成'"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    today = datetime.now()
    
    cursor.execute("""
        UPDATE sync_progress 
        SET status='completed', total_count=5200, updated_at=%s 
        WHERE task_name='full_market_sync'
    """, (today,))
    
    conn.close()
    logger.info(f"💾 DB状态已更新: full_market_sync = 今日 ({today})")

async def run_scheduler_test():
    # 1. 初始化DB为昨日
    update_db_to_yesterday()
    
    # 2. 启动调度器
    pool = MockPool()
    scheduler = AdaptiveKLineSyncScheduler(pool)
    
    # 为了测试快速进行，调整配置
    scheduler.sleep_check_interval_min = 0.05 # 3秒检查一次
    scheduler.poll_interval_min = 0.05       # 3秒轮询一次
    scheduler.history_buffer_min = 0         # 不提前，以当前时间为准
    
    # 3. 异步运行调度器
    logger.info("🚀 启动调度器任务...")
    scheduler_task = asyncio.create_task(scheduler.execute())
    
    # 4. 等待几秒，模拟等待过程
    logger.info("⏳ 等待5秒，模拟云端正在采集...")
    await asyncio.sleep(5)
    
    # 5. 更新DB为今日完成
    logger.info("⚡ 触发云端完成信号...")
    update_db_to_today()
    
    # 6. 等待调度器完成
    try:
        completion_time, count = await asyncio.wait_for(scheduler_task, timeout=10)
        logger.info(f"✅ 调度器成功完成! 检测到时间: {completion_time}, 数量: {count}")
        return True
    except asyncio.TimeoutError:
        logger.error("❌ 调度器超时未完成!")
        return False
    except Exception as e:
        logger.error(f"❌ 调度器发生异常: {e}")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(run_scheduler_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        pass
