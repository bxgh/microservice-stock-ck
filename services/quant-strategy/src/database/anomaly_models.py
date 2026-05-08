"""
Anomaly Signal Database Models
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Text, JSON, SmallInteger
from database.models import Base

class AnomalySignalModel(Base):
    """
    异动信号统一池模型 (ads_l8_unified_signal)
    """
    __tablename__ = 'ads_l8_unified_signal'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_version = Column(String(16), nullable=False, default='v1')
    user_id = Column(Integer, nullable=False, default=1)
    trade_date = Column(Date, nullable=False, index=True)
    ts_code = Column(String(20), nullable=False, index=True)
    name = Column(String(100))
    industry_sw1 = Column(String(100))
    industry_sw3 = Column(String(100))
    
    pool_type = Column(String(50), nullable=False)
    signal_type = Column(String(50), nullable=False)
    signal_subtype = Column(String(50))
    anomaly_category = Column(String(8), index=True) # C1/C2/C3/C4
    
    pct_chg = Column(Numeric(10, 6))
    turnover_rate = Column(Numeric(10, 6))
    volume_ratio_5d = Column(Numeric(10, 6))
    amount = Column(Numeric(20, 2))
    main_net_inflow = Column(Numeric(20, 2))
    
    signal_features = Column(JSON)
    tags = Column(JSON)
    
    resonance_level = Column(SmallInteger)
    resonance_dimensions = Column(JSON)
    resonance_score = Column(Numeric(10, 2))
    counter_signals = Column(JSON)
    counter_signal_score = Column(Numeric(10, 2))
    temporal_resonance = Column(JSON)
    
    raw_score = Column(Numeric(6, 2))
    score_l3_capital = Column(Numeric(6, 2))
    score_l4_emotion = Column(Numeric(6, 2))
    score_user_pref = Column(Numeric(6, 2))
    score_dedup_pen = Column(Numeric(6, 2))
    composite_score = Column(Numeric(6, 2))
    component_score = Column(JSON) # 评分分量溯源 JSON (E3-S2)
    
    excluded_reasons = Column(Text)
    default_visible = Column(SmallInteger, default=1)
    is_pushed = Column(SmallInteger, default=1)
    explanation_zh = Column(Text)
    
    extra = Column(JSON)
    schema_version = Column(String(16), default='v1.1')
    compute_version = Column(String(16))
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted = Column(SmallInteger, default=0)

    def __repr__(self):
        return f"<AnomalySignalModel(code={self.ts_code}, date={self.trade_date}, category={self.anomaly_category})>"

class MarketBriefModel(Base):
    """
    市场全景简报 (app_market_brief)
    """
    __tablename__ = 'app_market_brief'
    
    trade_date = Column(Date, primary_key=True)
    panorama_data = Column(JSON) # 包含涨跌家数、行业排名等
    ladder_data = Column(JSON)   # 包含连板梯队
    brief_summary = Column(Text) # LLM 综述 (可选)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted = Column(SmallInteger, default=0)
