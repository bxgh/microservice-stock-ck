import asyncio
import sys
import os
from datetime import datetime
import logging

# 将 src 目录添加到路径
sys.path.insert(0, '/app/src')

from collectors.datasource import DataSourceCollector
from writers.dual_writer import DualWriter
from writers.clickhouse import ClickHouseWriter
from writers.mysql_cloud import MySQLCloudWriter
from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sync-raw")

async def main():
    """同步单只股票的原始 K 线数据"""
    if len(sys.argv) < 2:
        print("Usage: python sync_raw.py <stock_code> [start_date] [end_date]")
        return

    stock_code = sys.argv[1]
    start_date = sys.argv[2] if len(sys.argv) > 2 else "2025-12-01"
    end_date = sys.argv[3] if len(sys.argv) > 3 else "2025-12-30"

    # 初始化组件
    clickhouse_writer = ClickHouseWriter()
    mysql_writer = MySQLCloudWriter()
    dual_writer = DualWriter(clickhouse_writer, mysql_writer)
    
    await dual_writer.initialize()
    
    collector = DataSourceCollector()
    await collector.initialize()

    try:
        # 格式化代码
        full_code = stock_code
        if not full_code.startswith(('sh.', 'sz.', 'bj.')):
            if full_code.startswith(('60', '68')):
                full_code = f"sh.{full_code}"
            elif full_code.startswith(('00', '30')):
                full_code = f"sz.{full_code}"

        logger.info(f"🚀 开始采集 {full_code} 的原始 K 线数据 ({start_date} -> {end_date})")
        
        # 采集数据 (使用刚才修改后的默认 adjustflag="3")
        data = await collector.collect_daily_kline(
            stock_code=full_code,
            start_date=start_date,
            end_date=end_date,
            adjustflag="3"  # 强制使用不复权
        )
        
        if data:
            logger.info(f"获取到 {len(data)} 条数据，首条: {data[0]['trade_date']}, 末条: {data[-1]['trade_date']}")
            # 写入数据库 (DualWriter 会处理 ClickHouse 和 MySQL)
            count = await dual_writer.write_kline(data)
            logger.info(f"✅ 成功写入 {count} 条数据到数据库")
        else:
            logger.warning(f"⚠️ 未获取到 {full_code} 的数据")

    except Exception as e:
        logger.error(f"❌ 同步失败: {e}", exc_info=True)
    finally:
        await dual_writer.close()
        await collector.close()

if __name__ == "__main__":
    asyncio.run(main())
