from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from src.storage.rdbms.database import Base

class StockPool(Base):
    """股票池模型"""
    __tablename__ = "stock_pools"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, comment="股票池名称")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="描述")
    strategy_type: Mapped[str] = mapped_column(String(50), default="manual", comment="策略类型: manual/auto")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # 关联
    items: Mapped[List["StockPoolItem"]] = relationship("StockPoolItem", back_populates="pool", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<StockPool(name={self.name})>"

class StockPoolItem(Base):
    """股票池成分股"""
    __tablename__ = "stock_pool_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pool_id: Mapped[int] = mapped_column(ForeignKey("stock_pools.id"), index=True)
    stock_code: Mapped[str] = mapped_column(String(20), index=True, comment="股票代码")
    stock_name: Mapped[Optional[str]] = mapped_column(String(100), comment="股票名称")
    weight: Mapped[float] = mapped_column(Float, default=1.0, comment="权重")
    
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # 关联
    pool: Mapped["StockPool"] = relationship("StockPool", back_populates="items")
    
    def __repr__(self):
        return f"<StockPoolItem(pool_id={self.pool_id}, code={self.stock_code})>"
