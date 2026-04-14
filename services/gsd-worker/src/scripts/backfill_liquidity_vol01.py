"""
2025-01-01 以来的历史数据回溯补录脚本 (VOL-01)
"""
import asyncio
import logging
import os
import sys
from datetime import datetime

# 注入路径以确保导入 analyzers 和 data_access
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from analyzers.liquidity_analyzer import LiquidityMomentumAnalyzer
from data_access.liquidity_dao import LiquidityDAO
from data_access.mysql_pool import MySQLPoolManager

logger = logging.getLogger(__name__)

async def backfill_liquidity_vol01():
    """补录 2025-01-01 至今的指标数据"""
    logger.info("Starting Backfill for VOL-01 (From 2025-01-01)...")
    
    # 1. 初始化
    mootdx_api_url = os.getenv("MOOTDX_API_URL", "http://172.17.0.1:8003")
    analyzer = LiquidityMomentumAnalyzer(mootdx_api_url=mootdx_api_url)
    dao = LiquidityDAO()
    
    try:
        # 2. 获取全量计算数据
        df = await analyzer.analyze_vol01()
        if df is None or df.empty:
            logger.error("Analysis failed: No data returned.")
            return
            
        # 3. 过滤数据范围自 2025-01-01 起
        backfill_df = df[df['datetime'] >= '2025-01-01']
        logger.info(f"Prepared {len(backfill_df)} trading days for backfill.")
        
        # 4. 批量迭代补录 (Upsert)
        count = 0
        for index, row in backfill_df.iterrows():
            trade_date = row['datetime'].strftime('%Y%m%d')
            upsert_info = {
                "trade_date": trade_date,
                "vol_ma_divergence": float(row['delta_vol'])
            }
            # 这里的 DAO 目前是一次一个，虽然可以优化为批量，
            # 但 300 条数据单次循环耗时亦在毫秒级，且能保证每条日期日志可见。
            await dao.upsert_liquidity_record(upsert_info)
            count += 1
            if count % 50 == 0:
                logger.info(f"Progress: {count}/{len(backfill_df)} days backfilled.")
                
        logger.info(f"✓ Backfill Finished: Successfully updated {count} records in MySQL.")
        
    except Exception as e:
        logger.error(f"Error in backfill: {e}")
    finally:
        await MySQLPoolManager.close_pool()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(backfill_liquidity_vol01())
