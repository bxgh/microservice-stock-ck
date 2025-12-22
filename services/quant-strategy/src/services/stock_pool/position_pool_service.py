"""
Position Pool Service

Manages active holdings, P&L tracking, and liquidity risk management.
"""
import logging
from datetime import date

from sqlalchemy import select

from adapters.stock_data_provider import data_provider
from database.position_models import PositionStock
from database.session import get_session

logger = logging.getLogger(__name__)


class PositionPoolService:
    """
    持仓池服务
    
    核心功能:
    1. 持仓管理 (CRUD)
    2. 流动性风险检查 (Pre-trade check)
    3. P&L 实时计算
    """

    def __init__(self):
        self._initialized = False

    async def initialize(self) -> None:
        """初始化服务"""
        if self._initialized:
            return
        await data_provider.initialize()
        self._initialized = True
        logger.info("PositionPoolService initialized")

    async def check_liquidity_risk(
        self,
        code: str,
        quantity: int,
        price: float
    ) -> tuple[str, str, float]:
        """
        交易前流动性检查
        
        计算拟交易金额与日均成交额的比率。
        
        Args:
            code: 股票代码
            quantity: 拟买入数量
            price: 拟买入价格
            
        Returns:
            (impact_level, warning_message, market_cap)
             impact_level: LOW, MEDIUM, HIGH
        """
        # 1. 获取股票市场数据
        stock_info = await data_provider.get_stock_info(code)
        if not stock_info:
            return "UNKNOWN", "无法获取股票数据", 0.0

        # 2. 获取日均成交额 (使用 current_volume 近似或从 universe 获取)
        # 理想情况应从 UniverseStock 获取准确的 20日均值
        # 这里简化处理，先尝试获取实时数据

        # 尝试从 Universe 获取更准确的 20日均值
        from database.stock_pool_models import UniverseStock
        avg_daily_volume = 0.0

        async for session in get_session():
            result = await session.execute(
                select(UniverseStock).where(UniverseStock.code == code)
            )
            uni_stock = result.scalar_one_or_none()
            if uni_stock and uni_stock.avg_turnover_20d:
                # 数据库存储的是万元
                avg_daily_volume = uni_stock.avg_turnover_20d * 10000

        if avg_daily_volume == 0:
             # 回退: 使用实时成交额的一定比例估算 (不准确，但有胜于无)
             realtime = await data_provider.get_realtime_quotes([code])
             if not realtime.empty:
                 avg_daily_volume = realtime.iloc[0]['volume'] * realtime.iloc[0]['price']

        if avg_daily_volume == 0:
            return "UNKNOWN", "无法获取成交额数据", 0.0

        # 3. 计算冲击成本
        position_value = quantity * price
        impact_ratio = position_value / avg_daily_volume

        impact_level = "LOW"
        msg = "流动性充裕"

        if impact_ratio > 0.10: # > 10%
            impact_level = "HIGH"
            msg = f"拟买入金额占比 {impact_ratio:.1%} (>10%)，流动性风险极高！"
        elif impact_ratio > 0.05: # > 5%
            impact_level = "MEDIUM"
            msg = f"拟买入金额占比 {impact_ratio:.1%} (>5%)，注意冲击成本"

        return impact_level, msg, avg_daily_volume

    async def add_position(
        self,
        code: str,
        name: str,
        entry_price: float,
        quantity: int,
        strategy_type: str,
        stop_loss: float | None = None
    ) -> PositionStock:
        """添加新持仓"""
        # 1. 进行流动性检查
        impact, msg, avg_vol = await self.check_liquidity_risk(code, quantity, entry_price)
        if impact == "HIGH":
            logger.warning(f"Adding HIGH risk position {code}: {msg}")

        async for session in get_session():
            position = PositionStock(
                code=code,
                name=name,
                entry_price=entry_price,
                quantity=quantity,
                strategy_type=strategy_type,
                entry_date=date.today(),
                current_price=entry_price,
                current_value=entry_price*quantity,
                profit_loss=0.0,
                profit_loss_pct=0.0,
                stop_loss=stop_loss,
                avg_daily_volume=avg_vol,
                liquidity_impact=impact,
                status='holding'
            )
            session.add(position)
            await session.commit()
            await session.refresh(position)
            logger.info(f"Added position {code}, liquidity impact: {impact}")
            return position

    async def get_all_positions(self) -> list[PositionStock]:
        """获取所有持仓"""
        async for session in get_session():
            result = await session.execute(
                select(PositionStock).where(PositionStock.status == 'holding')
            )
            return result.scalars().all()

position_pool_service = PositionPoolService()
