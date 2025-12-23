import logging
import asyncio
from datetime import datetime, timedelta
from collectors.datasource import DataSourceCollector
from writers.clickhouse import ClickHouseWriter
from writers.mysql_cloud import MySQLCloudWriter
from writers.dual_writer import DualWriter
from config.settings import settings

logger = logging.getLogger("data-collector.scheduler.jobs")

# 全局实例 (单例模式)
# 注意: 这些实例需要在 lifespan 中进行 initialize()
collector = DataSourceCollector()
ck_writer = ClickHouseWriter()
mysql_writer = MySQLCloudWriter()
dual_writer = DualWriter(ck_writer, mysql_writer)

async def daily_kline_job():
    """每日日K线采集任务"""
    logger.info("🔔 开始执行每日日K线采集任务...")
    
    try:
        # 1. 初始化资源 (幂等)
        await collector.initialize()
        await dual_writer.initialize()
        
        # 2. 获取股票列表
        stocks = await collector.get_stock_list()
        if not stocks:
            logger.warning("未获取到股票列表，跳过任务")
            return
            
        # 3. 确定采集日期 (当日)
        today = datetime.now().strftime("%Y-%m-%d")
        
        # P2.2: 追踪失败的股票
        failed_codes = []
        
        # 4. 并发采集
        semaphore = asyncio.Semaphore(settings.max_workers)
        
        async def collect_one(code, index):
            async with semaphore:
                if index % 100 == 0:
                    logger.info(f"正在处理第 {index}/{len(stocks)} 只股票: {code}")
                
                try:
                    data = await collector.collect_daily_kline(code, today, today)
                    if data:
                        counts = await dual_writer.write_kline(data)
                        return counts
                except Exception as e:
                    logger.error(f"采集股票 {code} 失败: {e}")
                    failed_codes.append(code)
                return {'clickhouse': 0, 'mysql': 0}

        tasks = [collect_one(code, i) for i, code in enumerate(stocks)]
        results = await asyncio.gather(*tasks)
        
        # 5. 统计结果
        total_ck = sum(r['clickhouse'] for r in results)
        total_ms = sum(r['mysql'] for r in results)
        
        logger.info(f"✅ 每日任务完成: CK写入 {total_ck} 条, MySQL写入 {total_ms} 条")
        
        # P2.2: 报告失败的股票
        if failed_codes:
            logger.warning(f"⚠️ {len(failed_codes)} 只股票采集失败，前10只: {failed_codes[:10]}")
        
    except Exception as e:
        logger.error(f"❌ 每日采集任务失败: {e}", exc_info=True)

async def backfill_history_job(start_date: str, end_date: str, codes: list = None):
    """历史补录任务"""
    logger.info(f"🔔 开始历史补录任务: {start_date} -> {end_date}")
    
    try:
        # 1. 初始化资源
        await collector.initialize()
        await dual_writer.initialize()
        
        if not codes:
            codes = await collector.get_stock_list()
            
        if not codes:
            logger.warning("未获取到股票列表，跳过补录任务")
            return

        semaphore = asyncio.Semaphore(settings.max_workers)
        
        async def collect_one(code, index):
            async with semaphore:
                if index % 10 == 0:
                    logger.info(f"历史补录进度: {index}/{len(codes)} ({code})")
                
                try:
                    data = await collector.collect_daily_kline(code, start_date, end_date)
                    if data:
                        await dual_writer.write_kline(data)
                except Exception as e:
                    logger.error(f"补录股票 {code} 失败: {e}")

        tasks = [collect_one(code, i) for i, code in enumerate(codes)]
        await asyncio.gather(*tasks)
                
        logger.info("✅ 历史补录任务完成")
    except Exception as e:
        logger.error(f"❌ 历史补录失败: {e}")
