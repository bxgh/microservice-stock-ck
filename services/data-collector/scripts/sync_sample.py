import asyncio
import logging
import sys
import os
from datetime import datetime

# 将 src 目录添加到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from scheduler.jobs import backfill_history_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sync-sample")

async def main():
    """同步指定股票的 K 线数据"""
    if len(sys.argv) < 2:
        print("Usage: python sync_sample.py <stock_code> [start_date] [end_date]")
        return

    stock_code = sys.argv[1]
    start_date = sys.argv[2] if len(sys.argv) > 2 else "2024-01-01"
    end_date = sys.argv[3] if len(sys.argv) > 3 else datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"🚀 开始为 {stock_code} 同步 K 线数据从 {start_date} 到 {end_date}")
    
    # 模拟股票代码格式 (sh.600519)
    if not stock_code.startswith(('sh.', 'sz.', 'bj.')):
        if stock_code.startswith(('60', '68')):
            stock_code = f"sh.{stock_code}"
        elif stock_code.startswith(('00', '30')):
            stock_code = f"sz.{stock_code}"
    
    # 执行补录任务
    await backfill_history_job(start_date, end_date, codes=[stock_code])
    
    logger.info(f"✨ {stock_code} 同步任务执行完毕")

if __name__ == "__main__":
    asyncio.run(main())
