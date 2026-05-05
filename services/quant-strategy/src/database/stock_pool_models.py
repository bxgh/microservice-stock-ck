"""
Stock Pool Database Models

SQLAlchemy async models for stock pool management.
Includes Universe Pool, Filter Config, and Pool Transition tracking.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String, Text

# Import Base from models to share metadata
from database.models import Base


class UniverseFilterConfig(Base):
    """
    Universe Pool 筛选配置 (动态可调)

    允许通过 API 修改筛选参数，无需重新部署。
    """
    __tablename__ = 'universe_filter_configs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_name = Column(String(50), nullable=False, unique=True, default='default')

    # 筛选参数 (可动态调整)
    min_list_months = Column(Integer, nullable=False, default=12)          # 上市最少月份
    min_avg_turnover = Column(Float, nullable=False, default=3000.0)       # 日均成交额 (万元)
    min_market_cap = Column(Float, nullable=False, default=30.0)           # 最小市值 (亿元)
    min_turnover_ratio = Column(Float, nullable=False, default=0.3)        # 最低换手率 (%)

    # 配置状态
    is_active = Column(Boolean, nullable=False, default=True)
    description = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self):
        return f"<UniverseFilterConfig(name={self.config_name}, active={self.is_active})>"


class UniverseStock(Base):
    """
    全市场基础池 (Universe Pool)

    存储通过筛选的股票列表，作为所有策略的输入源。
    数据持久化到腾讯云 MySQL。
    """
    __tablename__ = 'universe_stocks'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 股票基本信息
    code = Column(String(10), nullable=False, unique=True, index=True)
    name = Column(String(50), nullable=False)
    list_date = Column(Date, nullable=True)
    exchange = Column(String(10), nullable=True)  # SH/SZ/BJ

    # 行业分类 (用于相对评分)
    industry = Column(String(50), nullable=True)       # 行业名称（如"银行"、"房地产开发"）
    industry_code = Column(String(10), nullable=True)  # 行业代码（预留，用于标准化）

    # 流动性指标
    avg_turnover_20d = Column(Float, nullable=True)      # 日均成交额 (万元)
    market_cap = Column(Float, nullable=True)             # 总市值 (亿元)
    turnover_ratio_20d = Column(Float, nullable=True)     # 20日换手率 (%)

    # 筛选结果
    is_qualified = Column(Boolean, nullable=False, default=False)
    disqualify_reason = Column(String(200), nullable=True)

    # 时间戳
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        status = "✓" if self.is_qualified else "✗"
        return f"<UniverseStock({self.code} {self.name} [{status}])>"


class PoolTransition(Base):
    """
    池流转历史记录

    记录股票在不同池之间的流转，便于复盘和审计。
    """
    __tablename__ = 'pool_transitions'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 流转信息
    code = Column(String(10), nullable=False, index=True)
    from_pool = Column(String(50), nullable=True)   # 源池 (None 表示新进入)
    to_pool = Column(String(50), nullable=True)     # 目标池 (None 表示移出)
    transition_date = Column(DateTime, default=datetime.now, nullable=False, index=True)
    reason = Column(Text, nullable=True)

    # 评分变化 (可选)
    score_before = Column(Float, nullable=True)
    score_after = Column(Float, nullable=True)

    def __repr__(self):
        return f"<PoolTransition({self.code}: {self.from_pool} -> {self.to_pool})>"
