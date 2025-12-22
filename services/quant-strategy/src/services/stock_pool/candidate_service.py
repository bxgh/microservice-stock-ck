"""
Candidate Pool Service

Manages Long-term and Swing candidate pools, including scoring,
ranking, and sub-pool classification.

EPIC-002 Story 2.4: Integrated with real Alpha scoring services.
"""
import asyncio
import logging
from datetime import date

from sqlalchemy import delete, select

from adapters.stock_data_provider import StockDataProvider
from database.candidate_models import CandidateStock
from database.session import get_session
from database.stock_pool_models import UniverseStock
from services.alpha.fundamental_scoring_service import FundamentalScoringService, ScoringMode
from services.alpha.valuation_service import ValuationService

logger = logging.getLogger(__name__)

class CandidatePoolService:
    """
    候选池服务 (Enhanced with Real Alpha Scoring)
    
    Integrates:
    - FundamentalScoringService: ROE, Growth, Quality scoring
    - ValuationService: PE/PB historical band scoring
    """

    def __init__(
        self,
        data_provider: StockDataProvider,
        fundamental_scoring: FundamentalScoringService | None = None,
        valuation_service: ValuationService | None = None
    ):
        """
        Initialize with scoring services
        
        Args:
            data_provider: Data provider for fetching stock data
            fundamental_scoring: Fundamental scoring service (optional for backward compatibility)
            valuation_service: Valuation scoring service (optional for backward compatibility)
        """
        self.data_provider = data_provider
        self.fundamental_scoring = fundamental_scoring
        self.valuation_service = valuation_service

        # Scoring weights (60% fundamental + 40% valuation)
        self.fundamental_weight = 0.6
        self.valuation_weight = 0.4

        # Quality thresholds
        self.min_score_threshold = 60.0
        self.high_quality_threshold = 80.0
        self.medium_quality_threshold = 70.0

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

            # 2. 并发评分 (Real Alpha Scoring)
            logger.info(f"Scoring {len(universe_stocks)} stocks with real Alpha services...")

            # Rate limiting: Max 10 concurrent scoring tasks
            semaphore = asyncio.Semaphore(10)

            async def score_with_limit(stock):
                async with semaphore:
                    return await self._calculate_real_score(stock, pool_type)

            # Execute concurrent scoring
            score_tasks = [score_with_limit(stock) for stock in universe_stocks]
            scores = await asyncio.gather(*score_tasks, return_exceptions=True)

            # 3. 筛选与分类
            for stock, score_result in zip(universe_stocks, scores):
                # Handle exceptions
                if isinstance(score_result, Exception):
                    logger.warning(f"Scoring failed for {stock.code}: {score_result}")
                    continue

                score = score_result

                # Filter: Only high-quality stocks (score >= 60)
                if score is None or score < self.min_score_threshold:
                    logger.debug(f"Filtered out {stock.code}: score={score}")
                    continue

                # Classify into sub-pool
                sub_pool = self._classify_stock(stock, pool_type, score)

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

    async def _calculate_real_score(self, stock: UniverseStock, pool_type: str) -> float | None:
        """
        Real Alpha Scoring using FundamentalScoringService and ValuationService
        
        Args:
            stock: Universe stock to score
            pool_type: Pool type ('long' or 'swing')
            
        Returns:
            Combined score (0-100) or None if scoring fails
        """
        try:
            # For long-term pool, use fundamental + valuation scoring
            if pool_type == 'long':
                # Fallback to mock if services not injected
                if not self.fundamental_scoring or not self.valuation_service:
                    logger.warning("Scoring services not initialized, using mock scoring")
                    return self._calculate_mock_score(stock, pool_type)

                # 1. Fetch required data
                # 1. Get financial data
                financial_data = await self.data_provider.get_financial_indicators(stock.code)
                valuation_data = await self.data_provider.get_valuation(stock.code)

                # Get industry from UniverseStock for RELATIVE scoring
                industry_code = stock.industry  # 从数据库读取行业信息
                industry_stats = None
                if industry_code:
                    industry_stats = await self.data_provider.get_industry_stats(industry_code)

                # Calculate fundamental score
                fund_result = await self.fundamental_scoring.score_stock(
                    code=stock.code,
                    financials=financial_data,
                    industry_stats=industry_stats,
                    mode=ScoringMode.RELATIVE if industry_stats else ScoringMode.ABSOLUTE
                )

                # Calculate valuation score
                val_result = await self.valuation_service.score_stock(
                    code=stock.code,
                    current_valuation=valuation_data
                )

                # Combine scores
                if fund_result and val_result:
                    combined_score = (
                        fund_result.total_score * self.fundamental_weight +
                        val_result.total_score * self.valuation_weight
                    )
                    return round(combined_score, 2)

                logger.warning(f"Could not calculate score for {stock.code}")

                # Fallback to Mock Scoring if real scoring fails
                logger.warning(f"Falling back to mock scoring for {stock.code}")
                return self._calculate_mock_score(stock, pool_type)

            elif pool_type == 'swing':
                # Swing pool: Use mock scoring for now (TODO: implement smart money scoring)
                logger.debug(f"Using mock scoring for swing pool: {stock.code}")
                return self._calculate_mock_score(stock, pool_type)
            else:
                return None

        except Exception as e:
            logger.error(f"Scoring error for {stock.code}: {e}", exc_info=True)
            return None

    def _calculate_mock_score(self, stock: UniverseStock, pool_type: str) -> float:
        """
        Fallback mock scoring (for backward compatibility and swing pool)
        """
        seed = int(stock.code)
        import random
        r = random.Random(seed)

        if pool_type == 'long':
            base_score = 60
            if stock.market_cap and stock.market_cap > 500:
                base_score += 10
            if stock.turnover_ratio_20d and stock.turnover_ratio_20d > 1.0:
                base_score += 5
            noise = r.uniform(0, 25)
            return min(100.0, base_score + noise)
        elif pool_type == 'swing':
            base_score = 50
            if stock.turnover_ratio_20d and stock.turnover_ratio_20d > 2.0:
                base_score += 20
            elif stock.turnover_ratio_20d and stock.turnover_ratio_20d > 1.0:
                base_score += 10
            if stock.avg_turnover_20d and stock.avg_turnover_20d > 10000:
                base_score += 15
            money_flow_factor = r.uniform(-10, 30)
            total_score = base_score + money_flow_factor
            return min(100.0, max(0.0, total_score))
        else:
            return 50.0

    def _classify_stock(self, stock: UniverseStock, pool_type: str, score: float) -> str | None:
        """
        Enhanced sub-pool classification based on score and stock characteristics
        
        Args:
            stock: Universe stock
            pool_type: Pool type ('long' or 'swing')
            score: Alpha score (0-100)
            
        Returns:
            Sub-pool classification
        """
        if pool_type == 'long':
            # Score-based classification for long-term pool
            if score >= self.high_quality_threshold:
                # Top quality: Core holdings
                return 'core'
            elif score >= self.medium_quality_threshold:
                # Good quality: Growth candidates
                return 'growth'
            else:
                # Acceptable quality: Rotation candidates
                return 'rotation'

        elif pool_type == 'swing':
            # Momentum-based classification for swing pool
            if score >= self.high_quality_threshold:
                return 'momentum'
            elif score >= self.medium_quality_threshold:
                return 'mean_reversion'
            else:
                return 'oversold'

        return None

    async def get_candidates(
        self,
        pool_type: str,
        sub_pool: str | None = None,
        limit: int = 100
    ) -> list[CandidateStock]:
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

# NOTE: Global singleton initialization moved to main.py for proper dependency injection
# The service now requires:
#   - data_provider: StockDataProvider
#   - fundamental_scoring: FundamentalScoringService (optional)
#   - valuation_service: ValuationService (optional)
#
# Example initialization in main.py:
#   candidate_service = CandidatePoolService(
#       data_provider=stock_data_provider,
#       fundamental_scoring=fundamental_scoring_service,
#       valuation_service=valuation_service
#   )
