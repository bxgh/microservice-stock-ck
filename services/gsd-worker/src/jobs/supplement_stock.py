"""
定向个股数据补充任务入口

Usage:
    python -m jobs.supplement_stock --stocks 000001 600519 --data-types tick kline --date-range 20260101-20260115
"""
import sys
import logging
import asyncio
import argparse
from typing import List

from core.supplement_engine import DataSupplementEngine

# 配置日志
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("jobs.supplement_stock")

async def main():
    parser = argparse.ArgumentParser(description="定向个股数据补充任务")
    
    parser.add_argument("--stocks", nargs="+", required=True, help="股票代码列表 (e.g. 000001 600519)")
    parser.add_argument("--data-types", nargs="+", default=["tick"], help="数据类型 (e.g. tick kline financial)")
    parser.add_argument("--date", type=str, help="指定单日 (YYYYMMDD)")
    parser.add_argument("--date-range", type=str, help="指定日期范围 (YYYYMMDD-YYYYMMDD)")
    parser.add_argument("--priority", type=str, default="normal", help="任务优先级")
    
    args = parser.parse_args()
    
    # 构建参数字典
    params = {
        "stocks": args.stocks,
        "data_types": args.data_types,
        "priority": args.priority
    }
    
    if args.date:
        params["date"] = args.date
    if args.date_range and "-" in args.date_range:
        start, end = args.date_range.split("-")
        params["date_range"] = {"start": start, "end": end}
        
    logger.info(f"Received supplement command: {params}")
    
    engine = DataSupplementEngine()
    try:
        await engine.initialize()
        result = await engine.run(params)
        logger.info(f"Execution Result: {result}")
        if result["failed"] > 0:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Task Failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
