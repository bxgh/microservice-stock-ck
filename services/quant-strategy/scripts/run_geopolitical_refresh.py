import asyncio
import logging
import sys
import os
from datetime import datetime

# 设置路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from services.stock_pool.candidate_service import CandidatePoolService
from adapters.stock_data_provider import StockDataProvider
from services.alpha.fundamental_scoring_service import FundamentalScoringService
from services.alpha.valuation_service import ValuationService
from services.alpha.geopolitical_scoring_service import GeopoliticalScoringService
from strategies.geopolitical.scenario_detector import scenario_detector
from database.session import init_database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RefreshRealPool")

async def main():
    logger.info("Starting real Geopolitical Defense pool refresh...")
    await init_database()

    # 1. 初始化依赖组件
    data_provider = StockDataProvider()
    fundamental_scoring = FundamentalScoringService()
    valuation_service = ValuationService()
    geo_scoring = GeopoliticalScoringService()

    # 2. 初始化核心服务
    candidate_service = CandidatePoolService(
        data_provider=data_provider,
        fundamental_scoring=fundamental_scoring,
        valuation_service=valuation_service,
        geopolitical_scoring=geo_scoring,
        scenario_detector=scenario_detector
    )

    # 3. 执行刷新逻辑
    # 模拟时间设为 2026-03-05 (根据 IranWar_v2.md 设定)
    target_date = "2026-03-05"
    logger.info(f"Triggering refresh for date: {target_date}")
    
    try:
        count = await candidate_service.refresh_geopolitical_pool(target_date)
        logger.info(f"Successfully refreshed {count} stocks for geopolitical defense pool.")
        
        # 4. 打印 Top 20 结果
        candidates = await candidate_service.get_candidates(pool_type='geopolitical', limit=20)
        print("\n--- Top 20 Geopolitical Defense Candidates ---")
        for c in candidates:
            print(f"Rank {c.rank}: {c.code} | Score: {c.score:.2f} | Reason: {c.entry_reason}")
            
    except Exception as e:
        logger.error(f"Failed to refresh pool: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
