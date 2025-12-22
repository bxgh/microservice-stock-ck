from datetime import date

from sqlalchemy import Boolean, Column, Date, Float, Index, Integer, String, Text

from database.models import Base


class BlacklistStock(Base):
    __tablename__ = 'blacklist'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, unique=True)
    reason = Column(Text, nullable=False)
    # reason_type: 'tech_stop' | 'fundamental' | 'regulatory' | 'permanent'
    reason_type = Column(String(20), nullable=False)
    added_date = Column(Date, nullable=False, default=date.today)
    is_permanent = Column(Boolean, default=False)
    release_date = Column(Date, nullable=True)
    release_period_months = Column(Float, nullable=True) # 记录原本设定的期限
    loss_amount = Column(Float, nullable=True) # 如果是止损，记录亏损额

    # 索引优化查询
    __table_args__ = (
        Index('idx_blacklist_code_release', 'code', 'release_date'),
    )
