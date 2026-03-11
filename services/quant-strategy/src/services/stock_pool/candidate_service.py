"""
Candidate Pool Service

Manages Long-term and Swing candidate pools, including scoring,
ranking, and sub-pool classification.

EPIC-002 Story 2.4: Integrated with real Alpha scoring services.
"""
import asyncio
import logging
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import delete, select

from adapters.stock_data_provider import StockDataProvider
from database.candidate_models import CandidateStock
from database.session import get_session
from database.stock_pool_models import UniverseStock
from services.alpha.defense_factor_service import defense_factor_service
from services.alpha.fundamental_scoring_service import FundamentalScoringService, ScoringMode
from services.alpha.geopolitical_scoring_engine import geopolitical_scoring_engine
from services.alpha.valuation_service import ValuationService
from services.fundamental_filter import FundamentalFilter

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
        valuation_service: ValuationService | None = None,
        fundamental_filter: FundamentalFilter | None = None,
        geopolitical_scoring: Any | None = None,
        scenario_detector: Any | None = None
    ):
        """
        Initialize with scoring services

        Args:
            data_provider: Data provider for fetching stock data
            fundamental_scoring: Fundamental scoring service
            valuation_service: Valuation scoring service
            fundamental_filter: Hard-stop risk veto filter
        """
        self.data_provider = data_provider
        self.fundamental_scoring = fundamental_scoring
        self.valuation_service = valuation_service
        self.fundamental_filter = fundamental_filter
        self.geopolitical_scoring = geopolitical_scoring
        self.scenario_detector = scenario_detector

        # Scoring weights (60% fundamental + 40% valuation)
        self.fundamental_weight = 0.6
        self.valuation_weight = 0.4

        # Quality thresholds
        self.min_score_threshold = 60.0
        self.high_quality_threshold = 80.0
        self.medium_quality_threshold = 70.0

    async def refresh_pool(self, pool_type: str = 'long', limit: int | None = None) -> int:
        """
        刷新候选池
        1. 从 Universe 获取合格股票
        2. 计算评分 (Mock/Placeholder)
        3. 排序并保留 Top N
        4. 自动分类子池
        5. 持久化
        """
        logger.info(f"Refreshing {pool_type} candidate pool...")

        # 1. 检测当前地缘政治情景 (Story 19.3)
        from datetime import datetime
        scenario = None
        if self.scenario_detector:
            today_str = datetime.now().strftime("%Y-%m-%d")
            # 兼容模拟时间，如果是 T+1 脚本运行可能需要传入日期，此处默认用系统日期
            scenario = await self.scenario_detector.detect_scenario(today_str)
            logger.info(f"Geopolitical scenario detected: {scenario}")

            # 根据情景动态调整初始权重
            if self.geopolitical_scoring:
                self.fundamental_weight, self.valuation_weight = self.geopolitical_scoring.get_dynamic_weights(scenario)
                logger.info(f"Dynamic weights applied: Fundamental={self.fundamental_weight}, Valuation={self.valuation_weight}")

        async for session in get_session():
            # 1. 获取 Universe
            stmt = select(UniverseStock).where(UniverseStock.is_qualified.is_(True))
            universe_stocks = (await session.execute(stmt)).scalars().all()

            if not universe_stocks:
                logger.warning("Universe pool is empty, cannot refresh candidates.")
                return 0

            # 如果设置了快速选股限制
            if limit and limit < len(universe_stocks):
                import random
                universe_stocks = random.sample(universe_stocks, limit)
                logger.info(f"Randomly selected {limit} stocks from universe for quick test")

            # 1.5 风险否决 (Fundamental Veto Filter)
            if self.fundamental_filter:
                logger.info(f"Running risk veto filter on {len(universe_stocks)} universe stocks...")
                filter_result = await self.fundamental_filter.filter_stocks([s.code for s in universe_stocks])
                passed_codes = set(filter_result['passed'])
                universe_stocks = [s for s in universe_stocks if s.code in passed_codes]
                logger.info(f"Stocks remaining after veto: {len(universe_stocks)}")

            if not universe_stocks:
                logger.warning("All stocks were vetoed. Candidate pool is empty.")
                return 0

            candidates_data = []

            # 2. 并发评分 (Real Alpha Scoring)
            logger.info(f"Scoring {len(universe_stocks)} stocks with real Alpha services...")

            # Rate limiting: Max 10 concurrent scoring tasks
            semaphore = asyncio.Semaphore(50)

            async def score_with_limit(stock: UniverseStock, sem: asyncio.Semaphore) -> float | None:
                async with sem:
                    return await self._calculate_real_score(stock, pool_type)

            # Execute concurrent scoring
            score_tasks = [score_with_limit(stock, semaphore) for stock in universe_stocks]
            scores = await asyncio.gather(*score_tasks, return_exceptions=True)

            # 3. 提取另类数据生态红利 (Story 17.6)
            eco_bonuses = await self._get_eco_bonuses(universe_stocks)

            # 3.5 提取硬件底层红利 (Story 18.3)
            hw_bonuses = await self._get_hardware_bonuses(universe_stocks)

            # 3.6 提取地缘政治防御红利 (Story 19.3)
            gp_bonuses = {}
            if self.geopolitical_scoring and scenario:
                gp_bonuses = await self.geopolitical_scoring.get_geopolitical_bonuses(
                    [s.code for s in universe_stocks], scenario
                )

            # 4. 筛选与分类
            for stock, score_result in zip(universe_stocks, scores, strict=False):
                # Handle exceptions
                if isinstance(score_result, BaseException):
                    logger.warning(f"Scoring failed for {stock.code}: {score_result}")
                    continue

                raw_score = score_result

                # Filter: Only high-quality stocks (score >= 60)
                if raw_score is None or raw_score < self.min_score_threshold:
                    logger.debug(f"Filtered out {stock.code}: score={raw_score}")
                    continue

                score = raw_score
                entry_reason = f"Scored {raw_score:.1f} in {pool_type} model"

                # Apply Eco Bonus
                if stock.code in eco_bonuses:
                    bonus, reason = eco_bonuses[stock.code]
                    score = min(100.0, score + bonus)
                    entry_reason += f" | {reason} (+{bonus})"

                # Apply Hardware Bonus
                if stock.code in hw_bonuses:
                    bonus, reason = hw_bonuses[stock.code]
                    score = min(100.0, score + bonus)
                    entry_reason += f" | {reason} (+{bonus})"

                # Apply Geopolitical Defense Bonus (Story 19.3)
                if stock.code in gp_bonuses:
                    bonus, reason = gp_bonuses[stock.code]
                    score = min(100.0, score + bonus)
                    entry_reason += f" | {reason} (+{bonus})"

                # Classify into sub-pool
                sub_pool = self._classify_stock(stock, pool_type, score)

                candidates_data.append({
                    "code": stock.code,
                    "score": score,
                    "sub_pool": sub_pool,
                    "entry_reason": entry_reason
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
        return 0

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
        except Exception as e:
            logger.error(f"Error fetching data for scoring {stock.code}: {e}")
            return None

    async def _get_eco_bonuses(self, universe_stocks: list[UniverseStock]) -> dict[str, tuple[float, str]]:
        """
        Extracted logic for calculating ecosystem bonuses to allow easier testing.
        """
        eco_bonuses = {}  # type: dict[str, tuple[float, str]]  # code -> (bonus, reason)
        try:
            from config.altdata_mapping import get_concepts_for_label
            from dao.altdata import AltDataDAO

            alt_dao = AltDataDAO()
            signals_df = alt_dao.get_active_signals()
            print(f"DEBUG signals_df empty: {signals_df.empty}")
            if not signals_df.empty:
                concept_to_level = {}
                level_bonus = {"EXTREME": 15.0, "HOT": 10.0, "WARM": 5.0}

                for _, row in signals_df.iterrows():
                    concepts = get_concepts_for_label(row["label"])
                    print(f"DEBUG label: {row['label']}, concepts: {concepts}")
                    bonus = level_bonus.get(row["signal_level"], 0.0)
                    for c in concepts:
                        if c not in concept_to_level or concept_to_level[c]["bonus"] < bonus:
                            concept_to_level[c] = {
                                "bonus": bonus,
                                "label": row["label"],
                                "level": row["signal_level"]
                            }

                if concept_to_level:
                    print(f"DEBUG concept_to_level dict: {list(concept_to_level.keys())}")
                    from dao.industry import IndustryDAO
                    ind_dao = IndustryDAO()
                    # 批量查询 Universe 中的概念
                    concept_df = await ind_dao.get_stock_concepts([s.code for s in universe_stocks])
                    print(f"DEBUG concept_df empty: {concept_df.empty}")
                    if not concept_df.empty:
                        for _, row in concept_df.iterrows():
                            code = row["ts_code"]
                            c_name = row["sector_name"]
                            print(f"DEBUG testing code: {code}, concept: {c_name}")
                            if c_name in concept_to_level:
                                print(f"DEBUG matched: {code} -> {c_name}")
                                c_info = concept_to_level[c_name]
                                if code not in eco_bonuses or eco_bonuses[code][0] < c_info["bonus"]:
                                    eco_bonuses[code] = (
                                        c_info["bonus"],
                                        f"Eco[{c_info['label']}({c_info['level']})->{c_name}]"
                                    )
                        print(f"DEBUG final eco_bonuses: {eco_bonuses}")
        except Exception as e:
            logger.error(f"Fallback: Failed to inject ecosystem signals, ignoring: {e}")
        return eco_bonuses

    async def _get_hardware_bonuses(self, universe_stocks: list[UniverseStock]) -> dict[str, tuple[float, str]]:
        """
        聚合硬件另类信号 (GPU 价格, 政企投资) 并映射到个股加分 (Story 18.3)
        """
        hw_bonuses = {} # type: dict[str, tuple[float, str]]
        try:
            from dao.industry import IndustryDAO
            from services.alpha.hardware_signal_service import HardwareSignalService

            hw_service = HardwareSignalService()
            # 获取有效的概念加分映射 (e.g., {"昇腾概念": (8.0, "Hardware[Premium:910B]")})
            concept_bonuses = await hw_service.get_hardware_bonuses()

            if concept_bonuses:
                ind_dao = IndustryDAO()
                concept_df = await ind_dao.get_stock_concepts([s.code for s in universe_stocks])

                if not concept_df.empty:
                    for _, row in concept_df.iterrows():
                        code = row["ts_code"]
                        c_name = row["sector_name"]
                        if c_name in concept_bonuses:
                            bonus, reason = concept_bonuses[c_name]
                            if code not in hw_bonuses or hw_bonuses[code][0] < bonus:
                                hw_bonuses[code] = (bonus, reason)
        except Exception as e:
            logger.error(f"Failed to inject hardware signals: {e}")

        return hw_bonuses

    def _calculate_mock_score(self, stock: UniverseStock, pool_type: str) -> float:
        """
        Fallback mock scoring (for backward compatibility and swing pool)
        """
        try:
            # handle '600000.SH' format
            code_num = stock.code.split('.')[0] if '.' in stock.code else stock.code
            seed = int(code_num)
        except ValueError:
            seed = hash(stock.code)
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

    async def refresh_geopolitical_pool(self, current_date: str | None = None) -> int:
        """
        [NEW] EPIC-019 Story 19.5: 刷新地缘冲突防御型股票池
        """
        pool_type = 'geopolitical'
        logger.info("Refreshing Geopolitical Defense candidate pool...")

        if not current_date:
            current_date = date.today().strftime("%Y-%m-%d")

        if not self.scenario_detector or not self.geopolitical_scoring:
            logger.error("Geopolitical services not fully injected.")
            return 0

        # 1. 检测场景
        scenario = await self.scenario_detector.detect_scenario(current_date)
        logger.info(f"Targeting Scenario: {scenario} for date {current_date}")

        async for session in get_session():
            # 2. 获取 Universe
            stmt = select(UniverseStock).where(UniverseStock.is_qualified.is_(True))
            universe_stocks = (await session.execute(stmt)).scalars().all()
            if not universe_stocks:
                return 0

            # 3. 计算基础 Alpha 评分 (借用现有的计算逻辑，不持久化)
            logger.info(f"Scoring base alpha for {len(universe_stocks)} stocks...")
            semaphore = asyncio.Semaphore(50)
            async def score_task(stock: UniverseStock, sem: asyncio.Semaphore) -> float | None:
                async with sem:
                    return await self._calculate_real_score(stock, 'long')

            base_scores = await asyncio.gather(*[score_task(s, semaphore) for s in universe_stocks])

            # 4. 计算防御性特征指标 (Story 19.4)
            defense_factors_df = await defense_factor_service.compute_factors(
                [s.code for s in universe_stocks], current_date
            )

            # 5. 获取避险板块加分
            bonuses = await self.geopolitical_scoring.get_geopolitical_bonuses(
                [s.code for s in universe_stocks], scenario
            )

            # 6. 综合评分 (Story 19.5)
            # 组装基础得分
            base_df = pd.DataFrame([
                {"code": s.code, "score": sc if sc else 60.0}
                for s, sc in zip(universe_stocks, base_scores, strict=False)
            ])

            merged_df = pd.merge(base_df, defense_factors_df, on='code', how='inner')
            final_df = geopolitical_scoring_engine.score_defense(merged_df, bonuses, scenario)

            # 7. 持久化 (Top 20)
            await session.execute(
                delete(CandidateStock).where(CandidateStock.pool_type == pool_type)
            )

            rank = 1
            new_entries = []
            top_20 = final_df.head(20)

            for _, row in top_20.iterrows():
                entry = CandidateStock(
                    code=row["code"],
                    pool_type=pool_type,
                    sub_pool=str(scenario),
                    score=float(row["final_score"]),
                    rank=rank,
                    entry_date=date.today(),
                    entry_reason=f"GeopoliticalDefense[{scenario}]-Score:{row['final_score']:.1f}",
                    status='active'
                )
                new_entries.append(entry)
                rank += 1

            session.add_all(new_entries)
            await session.commit()

            logger.info(f"Successfully updated Geopolitical pool with {len(new_entries)} stocks.")
            return len(new_entries)
        return 0

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
