"""
Blacklist Service

Manages risk veto list, including adding stocks, checking status,
and cleaning up expired entries.
"""
import logging
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import delete, or_, select

from database.blacklist_models import BlacklistStock
from database.session import get_session

logger = logging.getLogger(__name__)

class BlacklistService:
    """
    黑名单服务
    
    核心功能:
    1. 添加黑名单 (自动计算解禁期)
    2. 检查黑名单 (Check)
    3. 清理过期 (Cleanup)
    """

    async def add_to_blacklist(
        self,
        code: str,
        reason: str,
        reason_type: str,
        loss_amount: float | None = None
    ) -> BlacklistStock:
        """
        添加到黑名单
        
        Args:
            code: 股票代码
            reason: 原因描述
            reason_type: 'tech_stop' (3mo), 'fundamental' (12mo), 'regulatory' (12mo), 'permanent'
            loss_amount: 亏损金额 (可选)
        """
        is_permanent = (reason_type == 'permanent')
        release_date = None
        period_months = 0

        today = date.today()

        if not is_permanent:
            if reason_type == 'tech_stop':
                period_months = 3
            elif reason_type in ['fundamental', 'regulatory']:
                period_months = 12
            else:
                period_months = 6 # Default

            release_date = today + relativedelta(months=period_months)

        async for session in get_session():
            # Check if exists, update if so
            result = await session.execute(select(BlacklistStock).where(BlacklistStock.code == code))
            existing = result.scalar_one_or_none()

            if existing:
                existing.reason = reason
                existing.reason_type = reason_type
                existing.added_date = today
                existing.is_permanent = is_permanent
                existing.release_date = release_date
                existing.release_period_months = period_months
                existing.loss_amount = loss_amount
                await session.commit()
                await session.refresh(existing)
                logger.info(f"Updated blacklist for {code}: {reason_type}, release: {release_date}")
                return existing
            else:
                new_entry = BlacklistStock(
                    code=code,
                    reason=reason,
                    reason_type=reason_type,
                    added_date=today,
                    is_permanent=is_permanent,
                    release_date=release_date,
                    release_period_months=period_months,
                    loss_amount=loss_amount
                )
                session.add(new_entry)
                await session.commit()
                await session.refresh(new_entry)
                logger.info(f"Added specific blacklist {code}: {reason_type}")
                return new_entry

    async def is_blacklisted(self, code: str) -> tuple[bool, str | None, date | None]:
        """
        检查是否在黑名单中
        
        Returns:
            (is_blacklisted, reason, release_date)
        """
        async for session in get_session():
            # 查找 code，且 (是永久 OR 解禁日期 > 今天)
            stmt = select(BlacklistStock).where(
                BlacklistStock.code == code,
                or_(
                    BlacklistStock.is_permanent.is_(True),
                    BlacklistStock.release_date > date.today()
                )
            )
            result = await session.execute(stmt)
            entry = result.scalar_one_or_none()

            if entry:
                return True, entry.reason, entry.release_date
            return False, None, None

    async def batch_check(self, codes: list[str]) -> dict[str, dict]:
        """批量检查黑名单"""
        results = {}
        async for session in get_session():
            stmt = select(BlacklistStock).where(
                BlacklistStock.code.in_(codes),
                or_(
                    BlacklistStock.is_permanent.is_(True),
                    BlacklistStock.release_date > date.today()
                )
            )
            db_results = (await session.execute(stmt)).scalars().all()

            blocked_map = {item.code: item for item in db_results}

            for code in codes:
                if code in blocked_map:
                    item = blocked_map[code]
                    results[code] = {
                        "is_blacklisted": True,
                        "reason": item.reason,
                        "release_date": item.release_date
                    }
                else:
                    results[code] = {"is_blacklisted": False}
        return results

    async def clean_expired_blacklist(self) -> int:
        """清理已过期的临时黑名单"""
        async for session in get_session():
            stmt = delete(BlacklistStock).where(
                BlacklistStock.is_permanent.is_(False),
                BlacklistStock.release_date <= date.today()
            )
            result = await session.execute(stmt)
            await session.commit()
            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired blacklist entries")
            return deleted_count

blacklist_service = BlacklistService()
