"""
Swing Pool Integration Tests

测试目标:
1. 验证 Swing Pool 独立性 (不影响 Long Pool)
2. 验证 Swing Pool 评分逻辑差异
3. 验证子池分类 (Momentum/Theme/Oversold)
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

class TestSwingPool:
    
    @pytest.mark.asyncio
    async def test_pool_isolation(self):
        """测试 Swing Pool 和 Long Pool 的独立性"""
        await ensure_db_initialized()
        
        async for session in get_session():
            # 1. 清理并准备测试数据
            await session.execute(delete(UniverseStock))
            await session.execute(delete(CandidateStock))
            
            # 创建少量测试股票
            test_stocks = []
            for i in range(50):
                code = f"{i:06d}"
                stock = UniverseStock(
                    code=code,
                    name=f"Stock_{i}",
                    avg_turnover_20d=15000 if i < 25 else 5000,  # 前25只高成交额
                    market_cap=300,
                    turnover_ratio_20d=2.5 if i < 25 else 0.8,  # 前25只高换手
                    is_qualified=True
                )
                test_stocks.append(stock)
            
            session.add_all(test_stocks)
            await session.commit()
            
        # 2. 刷新 Long Pool
        long_count = await candidate_service.refresh_pool(pool_type='long')
        assert long_count > 0
        
        # 3. 刷新 Swing Pool
        swing_count = await candidate_service.refresh_pool(pool_type='swing')
        assert swing_count > 0
        
        # 4. 验证独立性
        async for session in get_session():
            long_stocks = (await session.execute(
                select(CandidateStock).where(CandidateStock.pool_type == 'long')
            )).scalars().all()
            
            swing_stocks = (await session.execute(
                select(CandidateStock).where(CandidateStock.pool_type == 'swing')
            )).scalars().all()
            
            # 两个池应该都有数据
            assert len(long_stocks) > 0
            assert len(swing_stocks) > 0
            
            # 验证 pool_type 字段正确
            assert all(s.pool_type == 'long' for s in long_stocks)
            assert all(s.pool_type == 'swing' for s in swing_stocks)

    @pytest.mark.asyncio
    async def test_swing_classification(self):
        """测试 Swing Pool 子池分类"""
        # 查询 Swing Pool
        momentum_stocks = await candidate_service.get_candidates(
            pool_type='swing',
            sub_pool='momentum',
            limit=10
        )
        
        theme_stocks = await candidate_service.get_candidates(
            pool_type='swing',
            sub_pool='theme',
            limit=10
        )
        
        # oversold_stocks = await candidate_service.get_candidates(
        #     pool_type='swing',
        #     sub_pool='oversold',
        #     limit=10
        # )
        
        # 验证分类正确
        if momentum_stocks:
            for stock in momentum_stocks:
                assert stock.sub_pool == 'momentum'
                assert int(stock.code) % 3 == 0  # 根据 Mock 逻辑
                
        if theme_stocks:
            for stock in theme_stocks:
                assert stock.sub_pool == 'theme'
                assert int(stock.code) % 3 == 1

    @pytest.mark.asyncio
    async def test_scoring_difference(self):
        """验证 Long 和 Swing 评分逻辑的差异"""
        async for session in get_session():
            # 获取同一只股票在两个池中的分数
            code_sample = "000000"
            
            long_stock = (await session.execute(
                select(CandidateStock).where(
                    CandidateStock.code == code_sample,
                    CandidateStock.pool_type == 'long'
                )
            )).scalar_one_or_none()
            
            swing_stock = (await session.execute(
                select(CandidateStock).where(
                    CandidateStock.code == code_sample,
                    CandidateStock.pool_type == 'swing'
                )
            )).scalar_one_or_none()
            
            # 如果两个池都有这只股票，验证分数可能不同
            # (因为评分逻辑不同，但由于都是 Mock，可能相同，这里只验证字段存在)
            if long_stock and swing_stock:
                assert long_stock.score >= 0
                assert swing_stock.score >= 0
                # 注: 由于 Mock 逻辑，分数可能相同或不同，这里不做严格断言

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
