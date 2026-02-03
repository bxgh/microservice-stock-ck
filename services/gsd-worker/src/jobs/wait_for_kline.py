#!/usr/bin/env python3
"""
Job: wait_for_kline.py
功能：K线就绪探测器 (Gate-3 Barrier)
职责：
1. 循环探测 ClickHouse 中当日 K 线覆盖率
2. 达到阈值 (如 99.5%) 后释放下游流程
3. 带有超时机制，防止流程无限阻塞
"""

import asyncio
import logging
import sys
import argparse
import time
from datetime import datetime, timedelta
import pytz
from core.tick_sync_service import TickSyncService
from gsd_shared.utils.calendar_service import CalendarService

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("KlineProbe")
CST = pytz.timezone('Asia/Shanghai')

async def check_coverage(service: TickSyncService, trade_date: str) -> float:
    """计算当日数据覆盖率 (快照优先 -> K线降级)"""
    try:
        # 1. 获取预期总数 (Inventory)
        expected_codes = await service.stock_universe.get_all_a_stocks()
        expected_count = len(expected_codes)
        
        if expected_count == 0:
            logger.warning("⚠️ 无法获取预期股票名单，无法计算覆盖率")
            return 0.0

        actual_count = 0
        source_name = ""

        async with service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 优先尝试从快照分布式表中获取
                # 理由：快照数据比 K 线入库更及时
                snapshot_query = f"""
                SELECT count(DISTINCT stock_code) 
                FROM stock_data.snapshot_data_distributed 
                WHERE trade_date = '{trade_date}'
                """
                await cursor.execute(snapshot_query)
                row = await cursor.fetchone()
                snapshot_count = row[0] if row else 0

                if snapshot_count > 0:
                    actual_count = snapshot_count
                    source_name = "Snapshot (Distributed)"
                else:
                    # 降级方案：从 K 线表获取
                    kline_query = f"""
                    SELECT count() 
                    FROM stock_data.stock_kline_daily 
                    WHERE trade_date = '{trade_date}'
                    """
                    await cursor.execute(kline_query)
                    row = await cursor.fetchone()
                    actual_count = row[0] if row else 0
                    source_name = "K-Line (Daily)"

        coverage = (actual_count / expected_count) * 100
        logger.info(f"📊 数据就绪检查 [{source_name}]: 实际={actual_count}, 预期={expected_count}, 覆盖率={coverage:.2f}%")
        return coverage

    except Exception as e:
        logger.error(f"❌ 覆盖率检查异常: {e}")
        return 0.0

async def main():
    parser = argparse.ArgumentParser(description="K线就绪探测器")
    parser.add_argument("--date", type=str, help="YYYYMMDD")
    parser.add_argument("--threshold", type=float, default=99.5, help="覆盖率阈值 (%)")
    parser.add_argument("--timeout", type=int, default=3600, help="超时时间 (秒)")
    parser.add_argument("--interval", type=int, default=300, help="轮询间隔 (秒)")
    args = parser.parse_args()

    service = TickSyncService()
    await service.initialize()

    cal_service = CalendarService()

    # 1. 确定目标日期
    if args.date:
        try:
            dt = datetime.strptime(args.date, "%Y%m%d")
            trade_date = dt.strftime("%Y-%m-%d")
        except ValueError:
            trade_date = args.date
        
        # 对于手动指定的日期，若非交易日则直接报错退出
        if not cal_service.is_trading_day(trade_date):
            logger.error(f"❌ 手动指定的日期 {trade_date} 不是交易日，探测终止。")
            await service.close()
            sys.exit(1)
    else:
        now = datetime.now(CST)
        # 默认基准日期判定：凌晨 6 点前视为前一日的任务
        if now.hour < 6:
            base_date = (now - timedelta(days=1)).date()
        else:
            base_date = now.date()
        
        # 自动回溯逻辑：如果基准日期不是交易日，自动寻找上一个交易日
        target_dt = cal_service.get_last_trading_day(base_date)
        trade_date = target_dt.strftime("%Y-%m-%d")
        
        if trade_date != base_date.strftime("%Y-%m-%d"):
            logger.warning(f"ℹ️ 基准日期 {base_date} 非交易日，已自动修正为最近交易日: {trade_date}")

    start_time = time.time()
    logger.info(f"🚀 启动探测: 目标日期={trade_date}, 阈值={args.threshold}%, 超时={args.timeout}s")

    try:
        while True:
            # 2. 执行检查
            coverage = await check_coverage(service, trade_date)
            
            if coverage >= args.threshold:
                logger.info(f"✅ 基准数据就绪! 覆盖率 {coverage:.2f}% 已达到阈值 {args.threshold}%")
                # 正常退出，释放下游
                sys.exit(0)

            # 3. 超时检查
            elapsed = time.time() - start_time
            if elapsed > args.timeout:
                logger.error(f"❌ 探测超时! 已等待 {elapsed/60:.1f} 分钟，覆盖率仅为 {coverage:.2f}%")
                # 超时则报异常退出，阻止下游运行
                sys.exit(1)

            # 4. 等待下一轮
            logger.info(f"⏳ 数据尚未就绪 ({coverage:.2f}% < {args.threshold}%), {args.interval}s 后重试...")
            await asyncio.sleep(args.interval)

    except Exception as e:
        logger.error(f"❌ 探测 Job 奔溃: {e}")
        sys.exit(1)
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(main())
