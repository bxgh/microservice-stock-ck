"""
测试脚本：单股票数据采集验证
验证 DataSourceCollector 能否正确采集和写入数据
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_single_stock_collection():
    """测试单只股票的K线数据采集"""
    
    # 初始化组件
    clickhouse_writer = ClickHouseWriter()
    mysql_writer = MySQLCloudWriter()
    dual_writer = DualWriter(clickhouse_writer, mysql_writer)
    
    await clickhouse_writer.initialize()
    await mysql_writer.initialize()
    
    collector = DataSourceCollector()
    await collector.initialize()
    
    try:
        # 测试股票：贵州茅台 sh.600519
        test_code = "sh.600519"
        start_date = "2025-12-20"
        end_date = "2025-12-23"
        
        logger.info(f"开始采集 {test_code} 从 {start_date} 到 {end_date} 的数据")
        
        # 采集数据
        data = await collector.collect_daily_kline(
            stock_code=test_code,
            start_date=start_date,
            end_date=end_date,
            adjustflag="2"  # 前复权
        )
        
        if not data:
            logger.error("❌ 未采集到数据")
            return False
        
        logger.info(f"✅ 采集成功，共 {len(data)} 条记录")
        logger.info(f"样本数据: {data[0]}")
        
        # 写入数据库
        result = await dual_writer.write_kline(data)
        logger.info(f"写入结果: ClickHouse={result['clickhouse']} 条, MySQL={result['mysql']} 条")
        
        return result['clickhouse'] > 0
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False
    finally:
        await clickhouse_writer.close()
        await mysql_writer.close()
        await collector.close()

if __name__ == "__main__":
    success = asyncio.run(test_single_stock_collection())
    sys.exit(0 if success else 1)
