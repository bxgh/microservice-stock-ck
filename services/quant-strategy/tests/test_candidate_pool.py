"""
Candidate Pool Integration Tests

测试目标:
1. 从 Universe 刷新候选池逻辑
2. 评分排序与数量截断 (Top 300)
3. 子池分类 (红利/成长等)
4. API 数据一致性
"""
import pytest
import asyncio
from sqlalchemy import select, delete

from database import init_database
from database.session import get_session
from database.stock_pool_models import UniverseStock
from database.candidate_models import CandidateStock
from services.stock_pool.candidate_service import candidate_service

# Setup helper
_db_initialized = False

async def ensure_db_initialized():
    global _db_initialized
    if not _db_initialized:
        await init_database()
        _db_initialized = True

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

class TestCandidatePool:
    
    @pytest.mark.asyncio
    async def test_refresh_pool_logic(self):
        """测试候选池刷新逻辑"""
        await ensure_db_initialized()
        
        async for session in get_session():
            # 1. 准备测试数据: Universe 中插入不同特征的股票
            # 清理旧数据
            await session.execute(delete(UniverseStock))
            await session.execute(delete(CandidateStock))
            
            test_stocks = []
            for i in range(400): # 生成400只，测试Top 300截断
                code = f"{i:06d}"
                # 构造特征以触发不同分类和评分
                market_cap = 600 if i < 100 else 100 # 前100只大市值 -> 高分
                turnover_ratio = 1.5 if i < 50 else 0.5 # 前50只高换手 -> 更高分
                
                stock = UniverseStock(
                    code=code,
                    name=f"Stock_{i}",
                    avg_turnover_20d=5000,
                    market_cap=market_cap,
                    turnover_ratio_20d=turnover_ratio,
                    is_qualified=True
                )
                test_stocks.append(stock)
            
            session.add_all(test_stocks)
            await session.commit()
            
        # 2. 执行刷新
        count = await candidate_service.refresh_pool(pool_type='long')
        
        # 3. 验证结果
        assert count == 300 # Top 300 截断
        
        async for session in get_session():
            # 验证排序
            top_stocks = (await session.execute(
                select(CandidateStock)
                .where(CandidateStock.pool_type == 'long')
                .order_by(CandidateStock.rank.asc())
                .limit(10)
            )).scalars().all()
            
            # 第一名应该是分数最高的 (大市值+高换手)
            assert top_stocks[0].score >= top_stocks[-1].score
            assert top_stocks[0].rank == 1
            
            # 验证分类
            # 根据 Mock 逻辑: code % 3 == 0 -> dividend
            dividend_stock = (await session.execute(
                select(CandidateStock).where(
                    CandidateStock.pool_type == 'long',
                    CandidateStock.sub_pool == 'dividend'
                ).limit(1)
            )).scalar_one_or_none()
            assert dividend_stock is not None
            assert int(dividend_stock.code) % 3 == 0

    @pytest.mark.asyncio
    async def test_api_integration(self):
        """测试 API 集成 (通过 Service 调用模拟)"""
        # 查询红利池
        results = await candidate_service.get_candidates(
            pool_type='long',
            sub_pool='dividend',
            limit=10
        )
        assert len(results) > 0
        for stock in results:
            assert stock.sub_pool == 'dividend'
            assert stock.pool_type == 'long'

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
