import logging
import asyncio
from datetime import datetime, timedelta
from core.clickhouse_client import ClickHouseClient
from gsd_shared.utils.calendar_service import CalendarService

logger = logging.getLogger(__name__)

async def run():
    ch_client = ClickHouseClient()
    cal = CalendarService()
    
    try:
        await ch_client.connect()
        
        # 1. 精准确定归档日期（回溯寻找最近一个交易日）
        current_date = datetime.now().date()
        target_date = current_date - timedelta(days=1)
        # 循环回溯直到找到一个交易日
        while not cal.is_trading_day(target_date):
            target_date -= timedelta(days=1)
            
        target_date_str = target_date.strftime('%Y-%m-%d')
        logger.info(f"🚀 开始归档任务: 目标日期 = {target_date_str}")
        
        # 2. 统计待迁移数据量
        count_sql = f"SELECT count() FROM stock_data.tick_data_intraday WHERE trade_date = '{target_date_str}'"
        row_count = ch_client.execute(count_sql)[0][0]
        
        if row_count == 0:
            logger.warning(f"⚠️ {target_date_str} 无分笔数据需要迁移，跳过归档。")
        else:
            # 3. 原子迁移数据
            insert_sql = f"""
            INSERT INTO stock_data.tick_data 
            SELECT * FROM stock_data.tick_data_intraday 
            WHERE trade_date = '{target_date_str}'
            """
            logger.info(f"正在将 {row_count} 条记录迁移至历史表...")
            ch_client.execute(insert_sql)
            logger.info("✅ 迁移成功")
        
        # 4. 精准清理旧数据 (清理今日之前的所有零碎数据，确保当日表纯净)
        today_str = current_date.strftime('%Y-%m-%d')
        # 注意：分布式清理需在 _local 表上执行，并确保集群名称正确
        cleanup_sql = f"ALTER TABLE stock_data.tick_data_intraday_local ON CLUSTER 'stock_cluster' DELETE WHERE trade_date < '{today_str}'"
        logger.info(f"正在清理旧数据 (WHERE trade_date < {today_str})...")
        ch_client.execute(cleanup_sql)
        
        logger.info("🎉 [Gate-1.0] 归档与清理流程执行完毕")
        
    except Exception as e:
        logger.error(f"❌ 归档任务异常: {e}", exc_info=True)
        raise
    finally:
        ch_client.disconnect()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(run())
