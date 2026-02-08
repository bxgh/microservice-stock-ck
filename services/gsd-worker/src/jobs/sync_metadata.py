"""
Metadata 同步任务入口
用于同步股东、估值、大宗、龙虎榜等辅助数据
"""
import sys
import asyncio
import logging
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
from core.metadata_sync_service import MetadataSyncService
from core.job_context import job_ctx

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main(table: str = 'all', days: int = 7):
    """
    Metadata 同步主函数
    
    Args:
        table: 要同步的 MySQL 表名，'all' 表示全部同步
        days: 回溯天数（增量同步范围）
    """
    tz = ZoneInfo("Asia/Shanghai")
    start_time = datetime.now(tz)
    logger.info(f"启动 Metadata 同步任务 (Table={table}, Days={days})")
    
    service = MetadataSyncService()
    await service.initialize()
    
    try:
        if table == 'all':
            results = await service.sync_all(days=days)
        else:
            count = await service.sync_table(table, days=days)
            results = {table: count}
        
        # 统计结果
        total_records = sum(c for c in results.values() if c > 0)
        failed_tables = [t for t, c in results.items() if c < 0]
        
        status = "success" if not failed_tables else "partial_success"
        
        logger.info(f"✅ Metadata 同步任务完成 (Status={status}, Total={total_records})")
        
        # 报告给任务编排引擎
        job_ctx.update_output({
            "status": status,
            "results": results,
            "total_records": total_records,
            "failed_tables": failed_tables,
            "finish_time": datetime.now(tz).isoformat()
        })
        
        return 0 if status == "success" else 1
        
    except Exception as e:
        logger.error(f"❌ Metadata 同步任务异常: {e}", exc_info=True)
        job_ctx.set_output("error", str(e))
        job_ctx.set_output("status", "failed")
        return 1
    finally:
        job_ctx.flush_output()
        await service.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metadata 同步任务")
    parser.add_argument("--table", type=str, default="all", help="同步的目标表名 (MySQL)，默认为 all")
    parser.add_argument("--days", type=int, default=7, help="增量同步回溯天数，默认为 7")
    args = parser.parse_args()
    
    exit_code = asyncio.run(main(args.table, args.days))
    sys.exit(exit_code)
