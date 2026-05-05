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
    
    # 原始参数
    parser.add_argument("--stocks", nargs="*", help="股票代码列表")
    parser.add_argument("--data-types", nargs="+", default=["tick"], help="数据类型")
    parser.add_argument("--date", type=str, help="指定单日")
    parser.add_argument("--date-range", type=str, help="指定日期范围")
    parser.add_argument("--priority", type=str, default="normal", help="任务优先级")

    # 新增系统参数 (用于智能路由)
    parser.add_argument("--sys-action", type=str, help="系统动作: NONE, AI_AUDIT, FAILOVER")
    parser.add_argument("--sys-missing", type=str, help="缺失列表 (JSON/Str)")
    parser.add_argument("--sys-confirmed-bad", type=str, help="AI确认列表 (JSON/Str)")
    parser.add_argument("--force-concurrency", type=int, help="强制并发数")
    parser.add_argument("--concurrency-override", type=int, help="并发数覆盖 (同 force-concurrency)")
    parser.add_argument("--force-local", type=str, help="是否强制本地模式 (true/false)")
    parser.add_argument("--idempotent", type=str, default="true", help="是否执行幂等清理 (true/false)")
    parser.add_argument("--force", action="store_true", help="强制覆盖已有的高质量数据")

    args, unknown = parser.parse_known_args()
    if unknown:
        logger.info(f"Ignored unknown arguments: {unknown}")
    
    # ---------------------------------------------------------
    # 智能路由逻辑 (Smart Routing Logic)
    # ---------------------------------------------------------
    stocks_list = []
    engine_extra_config = {}

    if args.sys_action and args.sys_action != "NONE":
        # 由 Workflow 4.0 触发
        logger.info(f"🚦 Routing Mode: {args.sys_action}")
        
        # 1. 尝试从 sys_missing 提取
        if args.sys_missing and args.sys_missing != "[]" and args.sys_missing != "None":
            logger.info("Adding stocks from sys_missing")
            raw_missing = args.sys_missing
            clean_str = raw_missing.replace("[", "").replace("]", "").replace("'", "").replace('"', "")
            missing_list = [s.strip() for s in clean_str.split(',') if s.strip()]
            stocks_list.extend(missing_list)
        
        # 2. 尝试从 sys_confirmed_bad 提取
        if args.sys_confirmed_bad and args.sys_confirmed_bad != "[]" and args.sys_confirmed_bad != "None":
            logger.info("Adding stocks from sys_confirmed_bad")
            raw_bad = args.sys_confirmed_bad
            clean_str = raw_bad.replace("[", "").replace("]", "").replace("'", "").replace('"', "")
            bad_list = [s.strip() for s in clean_str.split(',') if s.strip()]
            stocks_list.extend(bad_list)
            
        # 3. 去重
        stocks_list = list(set(stocks_list))
        logger.info(f"Total stocks to process: {len(stocks_list)}")
        
        # 4. 特殊配置处理
        if args.sys_action == "FAILOVER" or str(args.force_local).upper() in ('TRUE', 'LOCAL'):
            logger.warning("Applying FAILOVER/LOCAL Config: Distributed Source -> NONE")
            engine_extra_config['distributed_source'] = 'none'

    elif args.stocks:
        # 手动/旧版触发
        raw_stocks = args.stocks
        if len(raw_stocks) == 1 and ',' in raw_stocks[0]:
            stocks_list = [s.strip() for s in raw_stocks[0].split(',') if s.strip()]
        else:
            stocks_list = raw_stocks
    else:
        logger.error("错误: 未提供有效股票列表 (--stocks 或 --sys-action)")
        sys.exit(1)

    if not stocks_list:
        logger.info("Empty stock list. Success.")
        return

    # ---------------------------------------------------------
    # 执行逻辑
    # ---------------------------------------------------------
    
    # 构建参数字典
    params = {
        "stocks": stocks_list,
        "data_types": args.data_types,
        "priority": args.priority,
        "force": args.force, # [NEW] Pass force flag
        "extra_config": engine_extra_config
    }
    
    # 并发控制覆盖
    if args.force_concurrency:
        params["concurrency_override"] = args.force_concurrency

    if args.date:
        params["date"] = args.date
    if args.date_range and "-" in args.date_range:
        start, end = args.date_range.split("-")
        params["date_range"] = {"start": start, "end": end}
    
    # 幂等控制
    params["idempotent"] = str(args.idempotent).lower() == "true"
    
    # 兼容 concurrency-override
    if args.concurrency_override:
        params["concurrency_override"] = args.concurrency_override
        
    logger.info(f"Target Count: {len(stocks_list)} stocks")
    # logger.info(f"Sample: {stocks_list[:5]}")
    
    engine = DataSupplementEngine()
    try:
        await engine.initialize()
        # 注意: 需要确保 DataSupplementEngine 支持 extra_config 参数
        # 或者我们需要在这里临时 patch 它的配置
        # 假设我们在此处只做个简单的逻辑，具体的 "force local" 
        # 可能需要 DataSupplementEngine 内部调用 sync_tick 时透传参数
        # 目前先传入，待 engine 适配
        result = await engine.run(params)
        
        logger.info(f"Execution Result: {result}")
        if result["failed"] > 0:
            # 如果大量失败，返回非零
            if result["failed"] > len(stocks_list) * 0.5:
                sys.exit(1)
            
    except Exception as e:
        logger.error(f"Task Failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
