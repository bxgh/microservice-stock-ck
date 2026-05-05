import asyncio
import sys
import logging
from pprint import pprint

sys.path.insert(0, '/home/bxgh/microservice-stock/services/quant-strategy/src')

from adapters.stock_data_provider import data_provider
from services.alpha.fundamental_scoring_service import fundamental_scoring_service
from services.alpha.valuation_service import valuation_service
from services.fundamental_filter import FundamentalFilter
from services.stock_pool.candidate_service import CandidatePoolService
from services.stock_pool.universe_pool_service import universe_pool_service
from database import init_database

logging.basicConfig(level=logging.INFO)

async def main():
    print("初始化数据库连接...")
    await init_database()
    
    print("初始化数据提供者和候选池服务...")
    # 强制初始化
    await data_provider.initialize()
    
    fundamental_filter_inst = FundamentalFilter()
    
    candidate_service = CandidatePoolService(
        data_provider=data_provider,
        fundamental_scoring=fundamental_scoring_service,
        valuation_service=valuation_service,
        fundamental_filter=fundamental_filter_inst
    )
    
    print("跳过 Universe 基础池同步以省时间...")
    
    print("开始刷新候选池 (使用线上真实数据 随机抽取400只测试)...")
    try:
        count = await candidate_service.refresh_pool(pool_type='long', limit=400)
        print(f"\n✅ 选股完成！共选出 {count} 只长线池候选股票。")
        
        print("\n🏆 Top 10 长线核心池标的:")
        results = await candidate_service.get_candidates(pool_type='long', limit=10)
        
        for idx, stock in enumerate(results, 1):
            print(f"{idx}. 代码: {stock.code} | 分数: {stock.score:.2f} | 细分池: {stock.sub_pool}")
            
    except Exception as e:
        print(f"执行失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())
