from sqlalchemy import Column, String, Date, Float, Integer, Index
from database.models import Base
from datetime import date

class CandidateStock(Base):
    __tablename__ = 'candidate_pool'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False)
    # pool_type: 'long' (长线) | 'swing' (波段)
    pool_type = Column(String(20), nullable=False)
    # sub_pool: 'dividend', 'growth', 'sector', 'momentum', 'theme', 'oversold'
    sub_pool = Column(String(50), nullable=True)
    
    score = Column(Float, nullable=False, default=0.0)
    rank = Column(Integer, nullable=False, default=9999)
    
    entry_date = Column(Date, nullable=False, default=date.today)
    entry_reason = Column(String(200), nullable=True)
    
    status = Column(String(20), default='active')  # active, removed

    # 复合索引优化查询: 按池类型+分数排序
    __table_args__ = (
        Index('idx_candidate_pool_score', 'pool_type', 'score'),
        Index('idx_candidate_code_pool', 'code', 'pool_type'),
    )
