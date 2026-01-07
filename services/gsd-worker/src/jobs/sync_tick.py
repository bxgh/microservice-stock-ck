"""
盘后分笔数据同步任务入口

供 task-orchestrator 调用的临时任务
"""

import sys
import asyncio
import logging
import argparse
from datetime import datetime
from core.tick_sync_service import TickSyncService
from core.task_logger import TaskLogger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main(mode: str = 'incremental', date: str = None, scope: str = "config") -> int:
    """
    分笔数据同步主函数
    
    Args:
        mode: 'incremental' (增量/今日) | 'full' (全量，仅用于测试)
        date: 指定日期 YYYYMMDD，默认今日
        scope: 'config' (配置文件) | 'all' (全市场)
        
    Returns:
        int: 退出码 (0: 成功, 1: 失败)
    """
    logger.info(f"启动分笔数据同步任务 (模式={mode}, 日期={date or '今日'}, 范围={scope})")
    
    service = TickSyncService()
    await service.initialize()
    
    start_time = datetime.now()
    
    try:
        # 获取股票池
        stock_codes = await service.get_all_stocks() if scope == "all" else await service.get_stock_pool()
        logger.info(f"待采集股票: {len(stock_codes)} 只")
        
        # 执行同步 (并发6: 3节点 × 2并发/节点)
        results = await service.sync_stocks(
            stock_codes=stock_codes,
            trade_date=date,
            concurrency=6
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # 判断结果
        if results["failed"] == 0:
            logger.info(
                f"✅ 分笔同步完成: "
                f"{results['success']} 只股票, "
                f"{results['total_records']:,} 条记录, "
                f"耗时 {duration:.1f}s"
            )
            return 0
        else:
            logger.warning(
                f"⚠️ 分笔同步部分失败: "
                f"成功 {results['success']}, 失败 {results['failed']}"
            )
            return 1 if results["failed"] > results["success"] else 0
            
    except Exception as e:
        logger.error(f"❌ 分笔同步任务异常: {e}", exc_info=True)
        return 1
    finally:
        await service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="分笔数据同步任务")
    parser.add_argument(
        "--mode", 
        type=str, 
        default="incremental",
        choices=["incremental", "full"],
        help="同步模式: incremental(增量/今日) 或 full(全量)"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="指定日期 YYYYMMDD，默认今日"
    )
    parser.add_argument("--scope", type=str, default="config", choices=["config", "all"], help="同步范围: config(配置文件) 或 all(全市场)")
    args = parser.parse_args()
    
    exit_code = asyncio.run(main(args.mode, args.date, args.scope))
    sys.exit(exit_code)
