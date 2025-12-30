"""
全市场股票 2025-12-23 K线数据批量采集
"""
import asyncio
import sys
sys.path.insert(0, '/app/src')

from collectors.datasource import DataSourceCollector
from writers.dual_writer import DualWriter
from writers.clickhouse import ClickHouseWriter
from writers.mysql_cloud import MySQLCloudWriter
from config.settings import settings
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def collect_all_stocks():
    """批量采集全市场股票K线数据"""
    
    # 初始化组件
    clickhouse_writer = ClickHouseWriter()
    mysql_writer = MySQLCloudWriter()
    dual_writer = DualWriter(clickhouse_writer, mysql_writer)
    
    await dual_writer.initialize()
    
    collector = DataSourceCollector()
    await collector.initialize()
    
    try:
        # 获取股票列表
        logger.info("正在获取全市场股票列表...")
        stock_codes = await collector.get_stock_list()
        
        if not stock_codes:
            logger.error("未获取到股票列表")
            return False
        
        logger.info(f"获取到 {len(stock_codes)} 只股票")
        
        # 批量采集配置
        target_date = "2025-12-23"
        batch_size = 50  # 每批50只股票
        semaphore = asyncio.Semaphore(settings.max_workers)  # 并发控制
        
        success_count = 0
        failed_count = 0
        total_rows = 0
        failed_stocks = []
        
        async def collect_one(code):
            nonlocal success_count, failed_count, total_rows
            
            async with semaphore:
                try:
                    # 采集数据
                    data = await collector.collect_daily_kline(
                        stock_code=code,
                        start_date=target_date,
                        end_date=target_date,
                        adjustflag="2"  # 前复权
                    )
                    
                    if data and len(data) > 0:
                        # 写入数据库
                        result = await dual_writer.write_kline(data)
                        success_count += 1
                        total_rows += len(data)
                        
                        if success_count % 100 == 0:
                            logger.info(f"进度: {success_count}/{len(stock_codes)} 只股票已完成")
                        
                        return True
                    else:
                        failed_count += 1
                        failed_stocks.append(code)
                        return False
                        
                except Exception as e:
                    logger.error(f"采集 {code} 失败: {e}")
                    failed_count += 1
                    failed_stocks.append(code)
                    return False
        
        # 开始批量采集
        logger.info(f"开始采集 {target_date} 全市场K线数据")
        logger.info(f"并发数: {settings.max_workers}")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        # 分批处理
        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(stock_codes) + batch_size - 1) // batch_size
            
            logger.info(f"\n【批次 {batch_num}/{total_batches}】处理 {len(batch)} 只股票")
            
            tasks = [collect_one(code) for code in batch]
            await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        # 统计结果
        logger.info("=" * 80)
        logger.info("📊 采集统计")
        logger.info(f"  总股票数: {len(stock_codes)}")
        logger.info(f"  成功: {success_count} 只")
        logger.info(f"  失败: {failed_count} 只")
        logger.info(f"  成功率: {success_count/len(stock_codes)*100:.2f}%")
        logger.info(f"  数据行数: {total_rows}")
        logger.info(f"  总耗时: {elapsed:.2f} 秒")
        logger.info(f"  平均速度: {len(stock_codes)/elapsed:.2f} 股票/秒")
        
        if failed_stocks:
            logger.warning(f"\n❌ 失败股票 ({len(failed_stocks)} 只):")
            logger.warning(f"  前20只: {failed_stocks[:20]}")
        
        logger.info("=" * 80)
        
        return success_count > 0
        
    except Exception as e:
        logger.error(f"批量采集失败: {e}", exc_info=True)
        return False
    finally:
        await dual_writer.close()
        await collector.close()

if __name__ == "__main__":
    success = asyncio.run(collect_all_stocks())
    sys.exit(0 if success else 1)
