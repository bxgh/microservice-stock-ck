"""
EPIC-005 Stock Pool System Integration Test

端到端测试场景:
1. Universe Pool 筛选 → 合格股票
2. Candidate Pool 评分 → Top 300 (Long/Swing)
3. Position Pool 建仓 → 流动性检查
4. Blacklist Pool 拦截 → 风控验证
"""
import asyncio
from datetime import date

import pytest
from sqlalchemy import delete, select

from database import init_database
from database.blacklist_models import BlacklistStock
from database.candidate_models import CandidateStock
from database.position_models import PositionStock
from database.session import get_session
from database.stock_pool_models import UniverseStock
from services.stock_pool.blacklist_service import blacklist_service
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

class TestEpic005Integration:

    @pytest.mark.asyncio
    async def test_full_pool_flow(self):
        """测试完整的股票池流转: Universe → Candidate → Position → Blacklist"""
        await ensure_db_initialized()

        # ========== Phase 1: Universe Pool ==========
        print("\n[Phase 1] Universe Pool Filtering")

        async for session in get_session():
            # 清理所有池
            await session.execute(delete(UniverseStock))
            await session.execute(delete(CandidateStock))
            await session.execute(delete(PositionStock))
            await session.execute(delete(BlacklistStock))

            # 创建测试数据: 100只股票
            test_stocks = []
            for i in range(100):
                code = f"{600000 + i:06d}"
                # 前50只合格, 后50只不合格 (ST股票)
                is_qualified = i < 50
                name = f"Stock_{i}" if is_qualified else f"ST_Stock_{i}"

                stock = UniverseStock(
                    code=code,
                    name=name,
                    avg_turnover_20d=8000 if is_qualified else 3000,
                    market_cap=400 if is_qualified else 50,
                    turnover_ratio_20d=1.2 if is_qualified else 0.3,
                    is_qualified=is_qualified,
                    disqualify_reason=None if is_qualified else "ST股票"
                )
                test_stocks.append(stock)

            session.add_all(test_stocks)
            await session.commit()

            # 验证 Universe
            qualified_count = (await session.execute(
                select(UniverseStock).where(UniverseStock.is_qualified.is_(True))
            )).scalars().all()

            print(f"  ✓ Universe Pool: {len(qualified_count)} qualified stocks")
            assert len(qualified_count) == 50

        # ========== Phase 2: Candidate Pool ==========
        print("\n[Phase 2] Candidate Pool Scoring & Ranking")

        # 刷新 Long Pool
        long_count = await candidate_service.refresh_pool(pool_type='long')
        print(f"  ✓ Long Candidate Pool: {long_count} stocks")
        assert long_count > 0

        # 刷新 Swing Pool
        swing_count = await candidate_service.refresh_pool(pool_type='swing')
        print(f"  ✓ Swing Candidate Pool: {swing_count} stocks")
        assert swing_count > 0

        # 验证池隔离
        async for session in get_session():
            long_stocks = (await session.execute(
                select(CandidateStock).where(CandidateStock.pool_type == 'long')
            )).scalars().all()

            swing_stocks = (await session.execute(
                select(CandidateStock).where(CandidateStock.pool_type == 'swing')
            )).scalars().all()

            assert len(long_stocks) > 0
            assert len(swing_stocks) > 0
            print(f"  ✓ Pool Isolation: Long={len(long_stocks)}, Swing={len(swing_stocks)}")

        # ========== Phase 3: Position Pool ==========
        print("\n[Phase 3] Position Pool (Simulated Trading)")

        # 从 Long Pool 选择 Top 5 建仓
        top_candidates = await candidate_service.get_candidates(
            pool_type='long',
            limit=5
        )

        async for session in get_session():
            for candidate in top_candidates:
                position = PositionStock(
                    code=candidate.code,
                    name=f"Stock_{candidate.code}",
                    strategy_type='long_term',
                    entry_price=100.0,
                    quantity=100,
                    entry_date=date.today(),
                    current_price=100.0,
                    profit_loss=0.0
                )
                session.add(position)
            await session.commit()

            positions = (await session.execute(select(PositionStock))).scalars().all()
            print(f"  ✓ Position Pool: {len(positions)} positions opened")
            assert len(positions) == 5

        # ========== Phase 4: Blacklist Pool ==========
        print("\n[Phase 4] Blacklist Pool (Risk Control)")

        # 将第一只持仓股票加入黑名单 (技术性止损)
        first_position_code = top_candidates[0].code
        await blacklist_service.add_to_blacklist(
            code=first_position_code,
            reason="技术性破位",
            reason_type="tech_stop",
            loss_amount=500.0
        )

        # 验证黑名单拦截
        is_blocked = await blacklist_service.is_blacklisted(first_position_code)
        print(f"  ✓ Blacklist Check: {first_position_code} is blocked = {is_blocked}")
        # is_blacklisted 返回 (bool, reason, release_date) 元组
        assert is_blocked[0] is True if isinstance(is_blocked, tuple) else is_blocked is True

        # 验证其他股票未被拦截
        second_position_code = top_candidates[1].code
        is_safe = await blacklist_service.is_blacklisted(second_position_code)
        assert is_safe is False or (isinstance(is_safe, tuple) and is_safe[0] is False)

        # ========== Phase 5: Data Consistency ==========
        print("\n[Phase 5] Data Consistency Verification")

        async for session in get_session():
            # 统计各池数量
            universe_count = len((await session.execute(
                select(UniverseStock).where(UniverseStock.is_qualified.is_(True))
            )).scalars().all())

            candidate_count = len((await session.execute(
                select(CandidateStock)
            )).scalars().all())

            position_count = len((await session.execute(
                select(PositionStock)
            )).scalars().all())

            blacklist_count = len((await session.execute(
                select(BlacklistStock)
            )).scalars().all())

            print("  ✓ Final State:")
            print(f"    - Universe: {universe_count}")
            print(f"    - Candidate: {candidate_count}")
            print(f"    - Position: {position_count}")
            print(f"    - Blacklist: {blacklist_count}")

            # 验证数据一致性
            assert universe_count == 50  # 合格股票
            assert candidate_count > 0   # 候选池有数据
            assert position_count == 5   # 5个持仓
            assert blacklist_count == 1  # 1个黑名单

        print("\n✅ EPIC-005 Integration Test PASSED")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
