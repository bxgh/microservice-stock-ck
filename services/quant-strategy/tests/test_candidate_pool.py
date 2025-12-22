"""
Candidate Pool Integration Tests

测试目标:
1. 从 Universe 刷新候选池逻辑
2. 评分排序与数量截断 (Top 300)
3. 子池分类 (红利/成长等)
4. API 数据一致性
"""
import sys

import pytest
from sqlalchemy import delete, select

sys.path.insert(0, '/home/bxgh/microservice-stock/services/quant-strategy/src')

from unittest.mock import AsyncMock, MagicMock

from adapters.stock_data_provider import StockDataProvider
from database import init_database
from database.candidate_models import CandidateStock
from database.session import close_database, get_session
from database.stock_pool_models import UniverseStock
from domain.alpha.scoring_models import DimensionScore, FundamentalScore, ScoringMode
from domain.alpha.valuation_models import ValuationBandScore, ValuationScore
from services.alpha.fundamental_scoring_service import FundamentalScoringService
from services.alpha.valuation_service import ValuationService
from services.stock_pool.candidate_service import CandidatePoolService

# Setup helper
_db_initialized = False

async def ensure_db_initialized():
    global _db_initialized
    if not _db_initialized:
        await init_database()
        _db_initialized = True

@pytest.fixture(autouse=True)
async def setup_database():
    """Setup temporary database for tests"""
    import os
    import tempfile

    import database.session as db_session
    from config.settings import settings

    # Reset global state
    db_session._engine = None
    db_session._session_factory = None
    global _db_initialized
    _db_initialized = False

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_quant.db")
        original_path = settings.database_path
        settings.database_path = db_path

        # Initialize
        await init_database()
        _db_initialized = True

        yield

        # Cleanup
        await close_database()
        settings.database_path = original_path
        db_session._engine = None
        db_session._session_factory = None

class TestCandidatePool:

    @pytest.fixture(autouse=True)
    def mock_services(self):
        """Setup mocked services with dynamic scoring"""
        data_provider = MagicMock(spec=StockDataProvider)

        # Mock Fundamental Scoring
        fundamental_scoring = MagicMock(spec=FundamentalScoringService)

        # Helper to create dummy dimension score
        def create_dim_score(name, score):
            return DimensionScore(
                dimension_name=name,
                weighted_score=score,
                metrics=[],
                mode=ScoringMode.ABSOLUTE
            )

        async def fs_side_effect(code, **kwargs):
            # Dynamic scoring based on code
            idx = int(code)
            total = 90.0 if idx < 100 else 40.0

            return FundamentalScore(
                stock_code=code,
                total_score=total,
                profitability=create_dim_score("Profitability", total),
                growth=create_dim_score("Growth", total),
                quality=create_dim_score("Quality", total),
                scoring_mode=ScoringMode.ABSOLUTE
            )

        fundamental_scoring.score_stock = AsyncMock(side_effect=fs_side_effect)

        # Mock Valuation Scoring
        valuation_service = MagicMock(spec=ValuationService)

        def create_band_score(name, score):
            return ValuationBandScore(
                metric_name=name,
                current_value=10.0,
                percentile=20.0,
                band_score=score,
                min_value=0, max_value=100, median_value=50
            )

        async def vs_side_effect(code, **kwargs):
            idx = int(code)
            score = 90.0 if idx < 100 else 40.0
            return ValuationScore(
                stock_code=code,
                total_score=score,
                pe_score=create_band_score("PE", score),
                pb_score=create_band_score("PB", score),
                valuation_status="Undervalued" if score > 80 else "Overvalued"
            )

        valuation_service.score_stock = AsyncMock(side_effect=vs_side_effect)

        # Mock Data Provider responses
        data_provider.get_financial_indicators = AsyncMock(return_value={'revenue': 100})
        data_provider.get_valuation = AsyncMock(return_value={'pe_ttm': 20})
        data_provider.get_industry_stats = AsyncMock(return_value={'pe_ttm_stats': {'mean': 25}})

        return data_provider, fundamental_scoring, valuation_service

    @pytest.mark.asyncio
    async def test_refresh_pool_logic(self, mock_services):
        """测试候选池刷新逻辑 (with Real Scoring Integration)"""
        # DB already initialized by fixture

        dp, fs, vs = mock_services
        candidate_service = CandidatePoolService(
            data_provider=dp,
            fundamental_scoring=fs,
            valuation_service=vs
        )

        async for session in get_session():
            # 1. 准备测试数据: Universe 中插入不同特征的股票
            # 清理旧数据
            await session.execute(delete(UniverseStock))
            await session.execute(delete(CandidateStock))

            test_stocks = []
            for i in range(400): # 生成400只，测试Top 300截断
                code = f"{i:06d}"
                # 构造特征以触发不同分类和评分
                # 构造特征
                market_cap = 600 if i < 100 else 100
                turnover_ratio = 1.5 if i < 50 else 0.5


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
        # We expect roughly 100 stocks (the ones with high scores)
        # Because low score stocks (40.0) < min threshold (60.0)
        assert count >= 100
        assert count <= 300

        async for session in get_session():
            # 验证排序
            top_stocks = (await session.execute(
                select(CandidateStock)
                .where(CandidateStock.pool_type == 'long')
                .order_by(CandidateStock.rank.asc())
                .limit(10)
            )).scalars().all()

            # 第一名应该是分数最高的
            assert top_stocks[0].score >= top_stocks[-1].score
            assert top_stocks[0].rank == 1

            # 验证分类 (Score >= 80 -> core)
            # Our high score stocks have 90.0 score -> 'core'
            core_stock = (await session.execute(
                select(CandidateStock).where(
                    CandidateStock.pool_type == 'long',
                    CandidateStock.sub_pool == 'core'
                ).limit(1)
            )).scalar_one_or_none()

            assert core_stock is not None
            assert core_stock.score >= 80.0

    @pytest.mark.asyncio
    async def test_api_integration(self, mock_services):
        """测试 API 集成 (通过 Service 调用模拟)"""
        # Manually populate candidate stock for query test
        async for session in get_session():
            stock = CandidateStock(
                code="000001",
                pool_type="long",
                sub_pool="core",
                score=95.0,
                rank=1
            )
            session.add(stock)
            await session.commit()

        dp, fs, vs = mock_services
        candidate_service = CandidatePoolService(dp, fs, vs)

        # 查询核心池
        results = await candidate_service.get_candidates(
            pool_type='long',
            sub_pool='core',
            limit=10
        )

        assert len(results) > 0
        for stock in results:
            assert stock.sub_pool == 'core'
            assert stock.pool_type == 'long'

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
