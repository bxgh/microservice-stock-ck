
"""
策略特征工程工厂 (StrategyFactory)
负责编排整个特征计算管线 (ETL -> Features -> Risk -> Store)
实现一键计算并存储全套特征矩阵
"""
import asyncio
import logging

import pandas as pd

from adapters.clickhouse_loader import ClickHouseLoader
from adapters.data_utils import DataValidator
from cache.feature_store import FeatureStore
from core.etl.cleaner import DataCleaner
from core.etl.data_quality_monitor import DataQualityMonitor
from core.features.basic_engine import BasicFeatureEngine
from core.features.trade_size_engine import TradeSizeEngine
from core.risk.liquidity_gatekeeper import LiquidityGatekeeper

logger = logging.getLogger(__name__)

class StrategyFactory:
    def __init__(self):
        self.loader = ClickHouseLoader()
        self.cleaner = DataCleaner()
        self.quality_monitor = DataQualityMonitor(loader=self.loader)
        self.basic_engine = BasicFeatureEngine(loader=self.loader)
        self.trade_size_engine = TradeSizeEngine(loader=self.loader)
        self.liquidity_gatekeeper = LiquidityGatekeeper(loader=self.loader)
        self.feature_store = FeatureStore()

    async def initialize(self):
        """批量初始化所有组件"""
        await self.loader.initialize()
        await self.cleaner.initialize()
        await self.basic_engine.initialize()
        await self.trade_size_engine.initialize()
        await self.liquidity_gatekeeper.initialize()
        logger.info("🚀 StrategyFactory components initialized")

    async def compute_and_store(self, stock_code: str, trade_date: str, skip_gate_check: bool = False) -> bool:
        """
        全量计算管线
        1. 代码标准化 (Gate-3)
        2. 数据质量门禁 (Gate-3)
        3. 数据加载与清洗 (Cleaner)
        4. 核心特征计算 (Basic/TradeSize/Liquidity)
        5. 拓扑与一致性终审 (Monitor)
        6. 压缩存储 (FeatureStore)
        """
        try:
            # 1. 代码标准化
            stock_code = DataValidator.clean_stock_code(stock_code)

            # 2. 质量初审 (Gate-3)
            # 检查 Redis 中的同步状态
            if not skip_gate_check:
                is_qualified, msg = await self.quality_monitor.is_qualified(stock_code, trade_date)
                if not is_qualified:
                    logger.warning(f"⚠️ Stock {stock_code} skipped: {msg}")
                    return False
            else:
                # 即使跳过 Gate-3，仍需基本活跃度确认 (K线对仗)
                is_active = await self.quality_monitor.check_if_active(stock_code, trade_date)
                if not is_active:
                    logger.warning(f"⚠️ Stock {stock_code} skipped: Not active on {trade_date}")
                    return False

            # 3. 数据加载
            ticks = await self.loader.get_ticks(stock_code, trade_date)
            snapshots = await self.loader.get_snapshots(stock_code, trade_date)

            if ticks.empty or snapshots.empty:
                logger.error(f"❌ Missing data for {stock_code}")
                return False

            # 4. 计算各个组件
            basic_feat_task = self.basic_engine.process_stock(stock_code, trade_date)
            trade_size_task = self.trade_size_engine.process_stock(stock_code, trade_date)
            liquidity_task = self.liquidity_gatekeeper.process_stock(stock_code, trade_date)

            basic_df, trade_size_df, liq_results = await asyncio.gather(
                basic_feat_task,
                trade_size_task,
                liquidity_task
            )

            # 5. 特征对齐与合并
            # 统一对齐到 240 分钟
            liq_df = liq_results['vpin']

            # 合并所有矩阵
            # Order: [vec_a, vec_b, vec_c, LOR, NLB, NLB_Ratio, RID, VPIN, Lambda]
            main_df = pd.concat([basic_df, trade_size_df, liq_df], axis=1)

            # 6. 数据质量终审 (Topology & Consistency)
            cleaned_snapshots = await self.cleaner.clean_snapshots_to_1min(snapshots)
            is_final_ok, final_msg = await self.quality_monitor.is_qualified(
                stock_code, trade_date,
                ticks_df=ticks,
                cleaned_df=cleaned_snapshots,
                snapshot_df=snapshots
            )

            # 针对历史数据跳过 Gate-3 状态限制，但保留拓扑校验结果
            if not is_final_ok:
                if skip_gate_check and "Gate-3 Status: MISSING" in final_msg:
                    logger.info(f"ℹ️ {stock_code} Gate-3 MISSING on {trade_date}, but proceeding as skip_gate_check=True")
                else:
                    logger.error(f"❌ Final quality check failed for {stock_code}: {final_msg}")
                    return False

            # 7. 存储
            feature_matrix = main_df.to_numpy()
            await self.feature_store.save_features(stock_code, trade_date, feature_matrix)

            logger.info(f"✅ Full pipeline completed for {stock_code} (Matrix: {feature_matrix.shape})")
            return True

        except Exception as e:
            logger.error(f"Pipeline error for {stock_code}: {e}", exc_info=True)
            return False

    async def close(self):
        """释放所有资源"""
        await self.loader.close()
        await self.basic_engine.close()
        await self.trade_size_engine.close()
        await self.liquidity_gatekeeper.close()
        logger.info("✅ StrategyFactory components closed")
