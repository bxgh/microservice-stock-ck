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
logger = logging.getLogger("bootstrap-kline")

async def main():
    """初始化 K 线数据"""
    start_date = os.getenv("START_DATE", "2024-01-01")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"🚀 开始初始化 K 线数据从 {start_date} 到 {end_date}")
    
    # 执行历史补录任务
    await backfill_history_job(start_date, end_date)
    
    logger.info("✨ 初始化任务执行完毕")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 任务被用户中断")
    except Exception as e:
        logger.error(f"❌ 运行失败: {e}")
