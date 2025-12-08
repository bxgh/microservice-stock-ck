from typing import List, Optional, Dict
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from src.storage.rdbms.database import db, AsyncDatabase
from src.storage.rdbms.models.stock_pool import StockPool, StockPoolItem
import logging

logger = logging.getLogger(__name__)

class StockPoolService:
    """股票池管理服务"""
    
    def __init__(self, database: AsyncDatabase = None):
        self.db = database or db

    async def get_pools(self) -> List[StockPool]:
        """获取所有股票池"""
        async with self.db.session() as session:
            stmt = select(StockPool).options(selectinload(StockPool.items))
            result = await session.execute(stmt)
            return result.scalars().all()

    async def create_pool(self, name: str, description: str = None, strategy_type: str = "manual") -> StockPool:
        """创建股票池"""
        async with self.db.session() as session:
            pool = StockPool(
                name=name,
                description=description,
                strategy_type=strategy_type
            )
            session.add(pool)
            await session.commit()
            await session.refresh(pool)
            return pool

    async def get_pool_by_id(self, pool_id: int) -> Optional[StockPool]:
        """获取指定股票池"""
        async with self.db.session() as session:
            stmt = select(StockPool).where(StockPool.id == pool_id).options(selectinload(StockPool.items))
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
            
    async def delete_pool(self, pool_id: int) -> bool:
        """删除股票池"""
        async with self.db.session() as session:
            stmt = select(StockPool).where(StockPool.id == pool_id)
            result = await session.execute(stmt)
            pool = result.scalar_one_or_none()
            if pool:
                await session.delete(pool)
                return True
            return False

    async def add_stock(self, pool_id: int, stock_code: str, stock_name: str = None, weight: float = 1.0) -> StockPoolItem:
        """添加股票到池中"""
        async with self.db.session() as session:
            # 检查池是否存在
            pool = await session.get(StockPool, pool_id)
            if not pool:
                raise ValueError(f"Pool {pool_id} not found")
            
            # 检查是否已存在
            stmt = select(StockPoolItem).where(
                StockPoolItem.pool_id == pool_id,
                StockPoolItem.stock_code == stock_code
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                # 更新
                existing.stock_name = stock_name or existing.stock_name
                existing.weight = weight
                await session.merge(existing)
                return existing
            
            # 新增
            item = StockPoolItem(
                pool_id=pool_id,
                stock_code=stock_code,
                stock_name=stock_name,
                weight=weight
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return item

    async def remove_stock(self, pool_id: int, stock_code: str) -> bool:
        """从池中移除股票"""
        async with self.db.session() as session:
            stmt = delete(StockPoolItem).where(
                StockPoolItem.pool_id == pool_id, 
                StockPoolItem.stock_code == stock_code
            )
            result = await session.execute(stmt)
            return result.rowcount > 0

    async def get_pool_stocks(self, pool_id: int) -> List[StockPoolItem]:
        """获取池中所有股票"""
        async with self.db.session() as session:
            stmt = select(StockPoolItem).where(StockPoolItem.pool_id == pool_id)
            result = await session.execute(stmt)
            return result.scalars().all()
