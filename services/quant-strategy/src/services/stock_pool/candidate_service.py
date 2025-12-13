"""
Candidate Pool Service

Manages Long-term and Swing candidate pools, including scoring,
ranking, and sub-pool classification.
"""
import logging
from datetime import date
from typing import List, Optional
from sqlalchemy import select, delete

from database.session import get_session
from database.candidate_models import CandidateStock
from database.stock_pool_models import UniverseStock

logger = logging.getLogger(__name__)

class CandidatePoolService:
    """
    候选池服务
    
    目前主要是长线候选池 (Long-term)
    """

    async def refresh_pool(self, pool_type: str = 'long') -> int:
        """
        刷新候选池
        1. 从 Universe 获取合格股票
        2. 计算评分 (Mock/Placeholder)
        3. 排序并保留 Top N
        4. 自动分类子池
        5. 持久化
        """
        logger.info(f"Refreshing {pool_type} candidate pool...")
        
        async for session in get_session():
            # 1. 获取 Universe
            stmt = select(UniverseStock).where(UniverseStock.is_qualified.is_(True))
            universe_stocks = (await session.execute(stmt)).scalars().all()
            
            if not universe_stocks:
                logger.warning("Universe pool is empty, cannot refresh candidates.")
                return 0
            
            candidates_data = []
            
            # 2. 评分与分类
            for stock in universe_stocks:
                # Mock Scoring: 实际逻辑将调用 EPIC-002 的 Alpha 4D
                score = self._calculate_mock_score(stock, pool_type)
                
                # 3. 筛选: 假设我们只关心分数 > 60 的
                if score < 60:
                    continue
                    
                sub_pool = self._classify_stock(stock, pool_type)
                
                candidates_data.append({
                    "code": stock.code,
                    "score": score,
                    "sub_pool": sub_pool,
                    "entry_reason": f"Scored {score:.1f} in {pool_type} model"
                })
            
            # 排序: 分数降序
            candidates_data.sort(key=lambda x: x["score"], reverse=True)
            
            # 保留 Top 300
            top_candidates = candidates_data[:300]
            
            # 4. 持久化 (全量替换该类型的池)
            # 先删除旧的 Active 记录 (或者标记为 removed, 这里简单起见先清空该类型的 active)
            # 实际生产可能需要 diff 更新，这里采用重建模式
            await session.execute(
                delete(CandidateStock).where(CandidateStock.pool_type == pool_type)
            )
            
            rank = 1
            new_entries = []
            today = date.today()
            
            for item in top_candidates:
                entry = CandidateStock(
                    code=item["code"],
                    pool_type=pool_type,
                    sub_pool=item["sub_pool"],
                    score=item["score"],
                    rank=rank,
                    entry_date=today,
                    entry_reason=item["entry_reason"],
                    status='active'
                )
                new_entries.append(entry)
                rank += 1
            
            session.add_all(new_entries)
            await session.commit()
            
            count = len(new_entries)
            logger.info(f"Refreshed {pool_type} pool with {count} candidates.")
            return count

    def _calculate_mock_score(self, stock: UniverseStock, pool_type: str) -> float:
        """
        模拟评分逻辑
        
        在 EPIC-002 完成前，使用市值和换手率生成一个 0-100 的随机分数
        """
        # 确定性 Mock: 保证同一只股票多次计算结果一致
        seed = int(stock.code)
        import random
        r = random.Random(seed)
        
        base_score = 60
        # 大市值加分
        if stock.market_cap and stock.market_cap > 500:
            base_score += 10
        # 活跃度加分
        if stock.turnover_ratio_20d and stock.turnover_ratio_20d > 1.0:
            base_score += 5
            
        noise = r.uniform(0, 25)
        return min(100.0, base_score + noise)

    def _classify_stock(self, stock: UniverseStock, pool_type: str) -> Optional[str]:
        """
        子池分类逻辑
        """
        if pool_type == 'long':
            # 简单规则 Mock
            # 实际上需要财务数据 (股息率, ROE等)
            # 这里暂时用 Code 和 交易所模拟
            
            code_int = int(stock.code)
            if code_int % 3 == 0:
                return 'dividend'
            elif code_int % 3 == 1:
                return 'growth'
            else:
                return 'sector'
                
        elif pool_type == 'swing':
            # 波段池分类
            code_int = int(stock.code)
            if code_int % 3 == 0:
                return 'momentum'
            elif code_int % 3 == 1:
                return 'theme'
            else:
                return 'oversold'
                
        return None

    async def get_candidates(
        self, 
        pool_type: str, 
        sub_pool: Optional[str] = None,
        limit: int = 100
    ) -> List[CandidateStock]:
        """查询候选池"""
        async for session in get_session():
            stmt = select(CandidateStock).where(
                CandidateStock.pool_type == pool_type,
                CandidateStock.status == 'active'
            )
            
            if sub_pool:
                stmt = stmt.where(CandidateStock.sub_pool == sub_pool)
                
            stmt = stmt.order_by(CandidateStock.rank.asc()).limit(limit)
            
            result = await session.execute(stmt)
            return result.scalars().all()

candidate_service = CandidatePoolService()
