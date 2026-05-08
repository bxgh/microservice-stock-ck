"""
ODS and ADS Models for Anomaly Scoring Job
"""
from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, SmallInteger, JSON, Text, BigInteger
from database.models import Base

class StockDerivedMetricsModel(Base):
    """
    派生指标层 (ads_stock_derived_metrics)
    """
    __tablename__ = 'ads_stock_derived_metrics'
    
    trade_date = Column(Date, primary_key=True)
    ts_code = Column(String(20), primary_key=True)
    
    volume_ratio_5d = Column(Numeric(10, 4))
    volume_ratio_20d = Column(Numeric(10, 4))
    cumulative_5d_pct = Column(Numeric(10, 6))
    industry_rank_pct_today = Column(Numeric(6, 4))
    dist_to_ma20 = Column(Numeric(10, 6))
    dist_to_ma250 = Column(Numeric(10, 6))
    
    is_deleted = Column(SmallInteger, default=0)

class EventLimitPoolModel(Base):
    """
    涨跌停池 (ods_event_limit_pool)
    """
    __tablename__ = 'ods_event_limit_pool'
    
    ts_code = Column(String(20), primary_key=True)
    trade_date = Column(Date, primary_key=True)
    pool_type = Column(String(16)) # zt, dt, zb, lian
    board_height = Column(SmallInteger)
    pct_chg = Column(Numeric(10, 6))
    
    is_deleted = Column(SmallInteger, default=0)

class HolderTradeModel(Base):
    """
    增减持公告 (ods_holdertrade)
    """
    __tablename__ = 'ods_holdertrade'
    
    id = Column(BigInteger, primary_key=True)
    ts_code = Column(String(20))
    ann_date = Column(Date)
    holder_name = Column(String(255))
    change_ratio = Column(Numeric(10, 6))
    direction = Column(String(10)) # 增持/减持
    
    is_deleted = Column(SmallInteger, default=0)

class RepurchaseModel(Base):
    """
    回购公告 (ods_repurchase)
    """
    __tablename__ = 'ods_repurchase'
    
    id = Column(BigInteger, primary_key=True)
    ts_code = Column(String(20))
    ann_date = Column(Date)
    repurchase_amount = Column(Numeric(20, 2))
    
    is_deleted = Column(SmallInteger, default=0)

class LhbDailyModel(Base):
    """
    龙虎榜 (stock_lhb_daily)
    """
    __tablename__ = 'stock_lhb_daily'
    
    id = Column(BigInteger, primary_key=True)
    ts_code = Column(String(20))
    trade_date = Column(Date)
    net_amount = Column(Numeric(20, 2))
    
    is_deleted = Column(SmallInteger, default=0)

class MarketBreadthModel(Base):
    """
    市场全景家数 (ods_market_breadth_daily)
    """
    __tablename__ = 'ods_market_breadth_daily'
    
    trade_date = Column(Date, primary_key=True)
    up_count = Column(Integer)
    down_count = Column(Integer)
    limit_up_count = Column(Integer)
    limit_down_count = Column(Integer)
    
    is_deleted = Column(SmallInteger, default=0)
