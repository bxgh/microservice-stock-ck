"""
Blacklist Pool Integration Tests

测试目标:
1. 黑名单添加与自动解禁日期计算
2. 批量检查 API
3. 过期清理逻辑
"""
import sys
from datetime import date, timedelta

import pytest
from dateutil.relativedelta import relativedelta

sys.path.insert(0, '/app/src')

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from sqlalchemy import delete  # noqa: E402

from database import init_database  # noqa: E402
from database.blacklist_models import BlacklistStock  # noqa: E402
from database.session import get_session  # noqa: E402
from services.stock_pool.blacklist_service import blacklist_service  # noqa: E402

# Setup helper
_db_initialized = False

async def ensure_db_initialized():
    global _db_initialized
    if not _db_initialized:
        await init_database()
        _db_initialized = True

class TestBlacklistService:
    """黑名单服务集成测试"""

    @pytest.mark.asyncio
    async def test_add_blacklist_expiration_logic(self):
        """测试不同类型的黑名单解禁期计算"""
        await ensure_db_initialized()

        # 1. 技术止损 (3个月)
        entry_tech = await blacklist_service.add_to_blacklist(
            code="TEST001",
            reason="Tech Stop",
            reason_type="tech_stop",
            loss_amount=1000.0
        )
        expected_date = date.today() + relativedelta(months=3)
        assert entry_tech.release_date == expected_date
        assert entry_tech.release_period_months == 3

        # 2. 基本面 (12个月)
        entry_fund = await blacklist_service.add_to_blacklist(
            code="TEST002",
            reason="Fundamental Fraud",
            reason_type="fundamental"
        )
        expected_date_fund = date.today() + relativedelta(months=12)
        assert entry_fund.release_date == expected_date_fund
        assert entry_fund.release_period_months == 12

        # 3. 永久
        entry_perm = await blacklist_service.add_to_blacklist(
            code="TEST003",
            reason="Delisted",
            reason_type="permanent"
        )
        assert entry_perm.is_permanent is True
        assert entry_perm.release_date is None

    @pytest.mark.asyncio
    async def test_batch_check(self):
        """测试批量检查接口"""
        await ensure_db_initialized()

        codes = ["TEST001", "TEST002", "SAFE001"]
        results = await blacklist_service.batch_check(codes)

        assert results["TEST001"]["is_blacklisted"] is True
        assert results["TEST001"]["reason"] == "Tech Stop"

        assert results["TEST002"]["is_blacklisted"] is True

        assert results["SAFE001"]["is_blacklisted"] is False

    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """测试过期清理逻辑"""
        await ensure_db_initialized()

        # 手动插入一个过期记录
        expired_date = date.today() - timedelta(days=1)
        code = "EXPIRED001"

        async for session in get_session():
            # 先清理可能存在的旧数据
            await session.execute(delete(BlacklistStock).where(BlacklistStock.code == code))

            expired_entry = BlacklistStock(
                code=code,
                reason="Old Stop",
                reason_type="tech_stop",
                added_date=date.today() - relativedelta(months=4),
                is_permanent=False,
                release_date=expired_date, # 昨天解禁
                release_period_months=3
            )
            session.add(expired_entry)
            await session.commit()

        # 验证插入成功
        is_blocked, _, _ = await blacklist_service.is_blacklisted(code)
        # 注意: is_blacklisted 已经排除了过期的，所以这里应该是 False
        # 但数据库里记录还在，直到 clean_expired_blacklist 被调用

        # 运行清理
        count = await blacklist_service.clean_expired_blacklist()
        assert count >= 1

        # 验证数据库中已删除
        async for session in get_session():
            from sqlalchemy import select
            res = await session.execute(select(BlacklistStock).where(BlacklistStock.code == code))
            assert res.scalar_one_or_none() is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
