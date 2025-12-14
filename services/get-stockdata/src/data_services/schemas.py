# -*- coding: utf-8 -*-
"""
EPIC-007 数据服务标准化 Schema 定义

定义各类数据的标准字段格式，确保不同数据源返回的数据格式一致。

@author: EPIC-007 Story 007.02
@date: 2025-12-06
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
import pandas as pd


@dataclass
class QuoteSchema:
    """实时行情标准字段定义
    
    所有 Provider 返回的行情数据必须符合此格式。
    
    字段说明:
        - code: 股票代码 (6位数字字符串)
        - name: 股票名称
        - price: 最新价 (当前价格)
        - open: 开盘价
        - high: 最高价
        - low: 最低价
        - close: 收盘价 (盘中=最新价)
        - pre_close: 昨收价
        - volume: 成交量 (手)
        - amount: 成交额 (元)
        - change: 涨跌额 (元)
        - change_pct: 涨跌幅 (%)
        - turnover: 换手率 (%, 可选)
        - timestamp: 数据时间戳
    """
    # 基础标识
    code: str
    name: str
    
    # 核心价格字段
    price: float
    open: float
    high: float
    low: float
    close: float
    pre_close: float
    
    # 成交统计
    volume: float  # 手
    amount: float  # 元
    
    # 涨跌统计
    change: float = 0.0  # 涨跌额
    change_pct: float = 0.0  # 涨跌幅
    
    # 可选字段
    turnover: Optional[float] = None  # 换手率
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 预留扩展字段（五档盘口等）
    extra: Dict = field(default_factory=dict)
    
    @staticmethod
    def get_required_columns() -> List[str]:
        """获取必需字段列表"""
        return [
            'code', 'name', 'price', 'open', 'high', 'low', 
            'close', 'pre_close', 'volume', 'amount',
            'change', 'change_pct'
        ]
    
    @staticmethod
    def get_optional_columns() -> List[str]:
        """获取可选字段列表"""
        return ['turnover', 'timestamp']
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> bool:
        """验证 DataFrame 是否符合标准格式
        
        Args:
            df: 待验证的 DataFrame
            
        Returns:
            bool: 是否符合标准
        """
        required = set(QuoteSchema.get_required_columns())
        actual = set(df.columns)
        return required.issubset(actual)


@dataclass
class QuoteWithOrderbookSchema(QuoteSchema):
    """带五档盘口的行情数据
    
    扩展标准行情，增加五档买卖盘信息。
    """
    # 买五档
    bid_price1: float = 0.0
    bid_volume1: int = 0
    bid_price2: float = 0.0
    bid_volume2: int = 0
    bid_price3: float = 0.0
    bid_volume3: int = 0
    bid_price4: float = 0.0
    bid_volume4: int = 0
    bid_price5: float = 0.0
    bid_volume5: int = 0
    
    # 卖五档
    ask_price1: float = 0.0
    ask_volume1: int = 0
    ask_price2: float = 0.0
    ask_volume2: int = 0
    ask_price3: float = 0.0
    ask_volume3: int = 0
    ask_price4: float = 0.0
    ask_volume4: int = 0
    ask_price5: float = 0.0
    ask_volume5: int = 0
    
    @staticmethod
    def get_orderbook_columns() -> List[str]:
        """获取盘口字段列表"""
        cols = []
        for i in range(1, 6):
            cols.extend([f'bid_price{i}', f'bid_volume{i}'])
            cols.extend([f'ask_price{i}', f'ask_volume{i}'])
        return cols


# ========== Story 007.02b: TickService Schema ==========

@dataclass
class TickSchema:
    """分笔成交标准字段定义
    
    所有 Provider 返回的分笔数据必须符合此格式。
    
    字段说明:
        - code: 股票代码 (6位数字字符串)
        - time: 成交时间 (HH:MM:SS)
        - price: 成交价格
        - volume: 成交量 (手)
        - amount: 成交额 (元)
        - direction: 买卖方向 (B=主动买入, S=主动卖出, N=中性)
        - tick_type: 成交类型 (0=买盘, 1=卖盘, 2=中性)
        - timestamp: 数据时间戳
    """
    code: str
    time: str  # HH:MM:SS
    price: float
    volume: int  # 手
    amount: float  # 元
    direction: str = 'N'  # B/S/N (买/卖/中性)
    tick_type: int = 2  # 0=买盘, 1=卖盘, 2=中性
    timestamp: datetime = field(default_factory=datetime.now)
    
    @staticmethod
    def get_required_columns() -> List[str]:
        """获取必需字段列表"""
        return ['code', 'time', 'price', 'volume', 'amount']
    
    @staticmethod
    def get_optional_columns() -> List[str]:
        """获取可选字段列表"""
        return ['direction', 'tick_type', 'timestamp']
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> bool:
        """验证 DataFrame 是否符合标准格式"""
        required = set(TickSchema.get_required_columns())
        actual = set(df.columns)
        return required.issubset(actual)


@dataclass
class CapitalFlowResult:
    """资金流向分析结果
    
    字段说明:
        - code: 股票代码
        - date: 交易日期
        - total_buy_amount: 主动买入总金额 (元)
        - total_sell_amount: 主动卖出总金额 (元)
        - net_inflow: 净流入 (元, 正数=流入, 负数=流出)
        - large_order_count: 大单笔数 (金额 >= 阈值)
        - large_order_amount: 大单总金额 (元)
        - buy_sell_ratio: 买卖比 (买入金额 / 卖出金额)
        - time_analysis: 分时段资金分析 (可选)
    """
    code: str
    date: str
    total_buy_amount: float
    total_sell_amount: float
    net_inflow: float
    large_order_count: int
    large_order_amount: float
    buy_sell_ratio: float
    time_analysis: Optional[Dict[str, Dict]] = None  # 分时段分析
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_inflow(self) -> bool:
        """是否净流入"""
        return self.net_inflow > 0
    
    @property
    def inflow_strength(self) -> str:
        """流入强度评级"""
        if self.net_inflow > 10_000_000:
            return "强流入"
        elif self.net_inflow > 5_000_000:
            return "中等流入"
        elif self.net_inflow > 0:
            return "弱流入"
        elif self.net_inflow > -5_000_000:
            return "弱流出"
        elif self.net_inflow > -10_000_000:
            return "中等流出"
        else:
            return "强流出"


# ========== Story 007.03: RankingService Schema ==========

class AnomalyType(str, Enum):
    """盘口异动类型枚举（完整的16种）
    
    基于东方财富网的盘口异动分类。
    """
    # === 上涨机会 (8种) ===
    ROCKET_LAUNCH = "火箭发射"        # 短时急涨(5分钟>3%)
    QUICK_REBOUND = "快速反弹"        # 从低位快速反弹
    LIMIT_UP_SEALED = "封涨停板"      # 封住涨停板
    LIMIT_DOWN_OPENED = "打开跌停板"  # 跌停板被打开
    TOUCH_LIMIT_UP = "触及涨停"       # 触及涨停未封住
    LARGE_BUY = "大笔买入"            # 大单买入(>50万)
    LARGE_BUY_QUEUE = "有大买盘"      # 大买盘堆积
    AUCTION_RALLY = "竞价上涨"        # 集合竞价大涨
    
    # === 风险预警 (8种) ===
    ACCELERATED_DECLINE = "加速下跌"  # 短时快速下跌
    HIGH_DIVE = "高台跳水"            # 高位急速跳水
    LIMIT_DOWN_SEALED = "封跌停板"    # 封住跌停板
    LIMIT_UP_OPENED = "打开涨停板"    # 涨停板被打开
    TOUCH_LIMIT_DOWN = "触及跌停"     # 触及跌停未封住
    LARGE_SELL = "大笔卖出"           # 大单卖出
    LARGE_SELL_QUEUE = "有大卖盘"     # 大卖盘堆积
    AUCTION_DECLINE = "竞价下跌"      # 集合竞价大跌
    
    # === 全部 ===
    ALL_ANOMALIES = "盘中异动"        # 全部类型异动


@dataclass
class RankingItem:
    """榜单项标准字段定义
    
    通用榜单数据结构，适用于人气榜、飙升榜等。
    
    字段说明:
        - rank: 排名
        - code: 股票代码 (6位数字字符串)
        - name: 股票名称
        - score: 评分/热度值 (可选)
        - change_pct: 涨跌幅 (%)
        - latest_price: 最新价 (元)
        - volume: 成交量 (手)
        - amount: 成交额 (元)
        - turnover_rate: 换手率 (%, 可选)
        - timestamp: 数据时间戳
        - metadata: 扩展字段（存储特殊榜单的额外信息）
    """
    # 基础标识
    rank: int
    code: str
    name: str
    
    # 核心字段
    change_pct: float
    latest_price: float
    
    # 成交统计
    volume: float = 0.0  # 手
    amount: float = 0.0  # 元
    
    # 可选字段
    score: Optional[float] = None  # 热度值/评分
    turnover_rate: Optional[float] = None  # 换手率
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 扩展字段（存储特殊信息）
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'RankingItem':
        """从字典创建RankingItem"""
        return RankingItem(
            rank=data.get('rank', 0),
            code=data.get('code', ''),
            name=data.get('name', ''),
            change_pct=data.get('change_pct', 0.0),
            latest_price=data.get('latest_price', 0.0),
            volume=data.get('volume', 0.0),
            amount=data.get('amount', 0.0),
            score=data.get('score'),
            turnover_rate=data.get('turnover_rate'),
            metadata=data.get('metadata', {})
        )


@dataclass
class LimitUpItem(RankingItem):
    """涨停池/连板榜单项
    
    扩展标准榜单，增加涨停特有字段。
    
    字段说明:
        - limit_up_time: 涨停时间 (HH:MM:SS)
        - open_count: 开板次数
        - continuous_days: 连板天数
        - first_limit_up_time: 首次涨停时间 (可选)
        - reason: 涨停原因/概念 (可选)
    """
    limit_up_time: str = ""  # 涨停时间
    open_count: int = 0  # 开板次数
    continuous_days: int = 0  # 连板天数
    first_limit_up_time: Optional[str] = None  # 首次涨停时间
    reason: Optional[str] = None  # 涨停原因
    
    @staticmethod
    def from_ranking_item(item: RankingItem, **kwargs) -> 'LimitUpItem':
        """从RankingItem创建LimitUpItem"""
        return LimitUpItem(
            rank=item.rank,
            code=item.code,
            name=item.name,
            change_pct=item.change_pct,
            latest_price=item.latest_price,
            volume=item.volume,
            amount=item.amount,
            score=item.score,
            turnover_rate=item.turnover_rate,
            timestamp=item.timestamp,
            metadata=item.metadata,
            **kwargs
        )


@dataclass
class DragonTigerItem(RankingItem):
    """龙虎榜榜单项
    
    扩展标准榜单，增加龙虎榜特有字段。
    
    字段说明:
        - net_amount: 净买入额 (元, 正数=净买入, 负数=净卖出)
        - buy_amount: 买入总额 (元)
        - sell_amount: 卖出总额 (元)
        - reason: 上榜原因 (如"日涨幅偏离值达7%")
        - institution_count: 机构席位数
    """
    net_amount: float = 0.0  # 净买入额
    buy_amount: float = 0.0  # 买入总额
    sell_amount: float = 0.0  # 卖出总额
    reason: str = ""  # 上榜原因
    institution_count: int = 0  # 机构席位数
    
    @property
    def is_net_buy(self) -> bool:
        """是否净买入"""
        return self.net_amount > 0
    
    @staticmethod
    def from_ranking_item(item: RankingItem, **kwargs) -> 'DragonTigerItem':
        """从RankingItem创建DragonTigerItem"""
        return DragonTigerItem(
            rank=item.rank,
            code=item.code,
            name=item.name,
            change_pct=item.change_pct,
            latest_price=item.latest_price,
            volume=item.volume,
            amount=item.amount,
            score=item.score,
            turnover_rate=item.turnover_rate,
            timestamp=item.timestamp,
            metadata=item.metadata,
            **kwargs
        )


# Legacy alias for backward compatibility
RankingSchema = RankingItem


# 字段映射工具
class FieldMapper:
    """字段映射工具
    
    用于将不同数据源的字段名映射到标准字段。
    """
    
    # mootdx 字段映射
    MOOTDX_MAPPING = {
        'code': 'code',
        'name': 'name',
        'price': 'price',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'last_close': 'pre_close',  # mootdx 用 last_close
        'vol': 'volume',
        'amount': 'amount',
        # 盘口字段
        'bid1': 'bid_price1',
        'bid_vol1': 'bid_volume1',
        'bid2': 'bid_price2',
        'bid_vol2': 'bid_volume2',
        'bid3': 'bid_price3',
        'bid_vol3': 'bid_volume3',
        'bid4': 'bid_price4',
        'bid_vol4': 'bid_volume4',
        'bid5': 'bid_price5',
        'bid_vol5': 'bid_volume5',
        'ask1': 'ask_price1',
        'ask_vol1': 'ask_volume1',
        'ask2': 'ask_price2',
        'ask_vol2': 'ask_volume2',
        'ask3': 'ask_price3',
        'ask_vol3': 'ask_volume3',
        'ask4': 'ask_price4',
        'ask_vol4': 'ask_volume4',
        'ask5': 'ask_price5',
        'ask_vol5': 'ask_volume5',
    }
    
    # mootdx 分笔数据字段映射
    MOOTDX_TICK_MAPPING = {
        'time': 'time',      # 成交时间
        'price': 'price',    # 成交价格
        'vol': 'volume',     # 成交量 (手)
        'amount': 'amount',  # 成交额 (元)
        'type': 'tick_type', # 成交类型 (0=买盘, 1=卖盘, 2=中性)
    }
    
    # akshare 榜单字段映射 (Story 007.03)
    AKSHARE_RANKING_MAPPING = {
        # 通用榜单字段
        '序号': 'rank',
        '排名': 'rank',
        '代码': 'code',
        '股票代码': 'code',
        '名称': 'name',
        '股票名称': 'name',
        '最新价': 'latest_price',
        '现价': 'latest_price',
        '涨跌幅': 'change_pct',
        '成交量': 'volume',
        '成交额': 'amount',
        '换手率': 'turnover_rate',
        '人气': 'score',
        '热度': 'score',
        
        # 涨停池特有字段
        '涨停价格': 'latest_price',
        '首次封板时间': 'limit_up_time',
        '封板时间': 'limit_up_time',
        '连板数': 'continuous_days',
        '连续涨停天数': 'continuous_days',
        '开板次数': 'open_count',
        '涨停原因': 'reason',
        '所属概念': 'reason',
        
        # 龙虎榜特有字段
        '净买入': 'net_amount',
        '净额': 'net_amount',
        '买入额': 'buy_amount',
        '卖出额': 'sell_amount',
        '上榜原因': 'reason',
        '机构数': 'institution_count',
    }
    
    # easyquotation 字段映射 (实际返回字段)
    EASYQUOTATION_MAPPING = {
        '股票代码': 'code',
        'code': 'code',  # 有时返回英文
        '股票名称': 'name',
        'name': 'name',
        '现价': 'price',
        'now': 'price',  # easyquotation 返回 'now'
        '今开': 'open',
        'open': 'open',
        '最高': 'high',
        'high': 'high',
        '最低': 'low',
        'low': 'low',
        '昨收': 'pre_close',
        'close': 'pre_close',  # easyquotation 的 close 实际是昨收
        '成交量': 'volume',
        'turnover': 'volume',  # 注意：easyquotation的turnover是成交量（手）
        '成交额': 'amount',
        'volume': 'amount',  # easyquotation的volume是成交额（元）
        '涨跌额': 'change',
        '涨跌幅': 'change_pct',
        '换手率': 'turnover',
        # 五档盘口
        'bid1': 'bid_price1',
        'bid1_volume': 'bid_volume1',
        'bid2': 'bid_price2',
        'bid2_volume': 'bid_volume2',
        'bid3': 'bid_price3',
        'bid3_volume': 'bid_volume3',
        'bid4': 'bid_price4',
        'bid4_volume': 'bid_volume4',
        'bid5': 'bid_price5',
        'bid5_volume': 'bid_volume5',
        'ask1': 'ask_price1',
        'ask1_volume': 'ask_volume1',
        'ask2': 'ask_price2',
        'ask2_volume': 'ask_volume2',
        'ask3': 'ask_price3',
        'ask3_volume': 'ask_volume3',
        'ask4': 'ask_price4',
        'ask4_volume': 'ask_volume4',
        'ask5': 'ask_price5',
        'ask5_volume': 'ask_volume5',
    }
    
    @staticmethod
    def map_columns(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """应用字段映射
        
        Args:
            df: 原始 DataFrame
            mapping: 字段映射字典
            
        Returns:
            pd.DataFrame: 映射后的 DataFrame
        """
        # 只映射存在的字段
        rename_dict = {k: v for k, v in mapping.items() if k in df.columns}
        return df.rename(columns=rename_dict)
    
    @staticmethod
    def calculate_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
        """计算派生字段
        
        如果缺少 change/change_pct，根据 price 和 pre_close 计算。
        
        Args:
            df: DataFrame
            
        Returns:
            pd.DataFrame: 添加派生字段后的 DataFrame
        """
        df = df.copy()
        
        # 计算涨跌额
        if 'change' not in df.columns and 'price' in df.columns and 'pre_close' in df.columns:
            df['change'] = df['price'] - df['pre_close']
        
        # 计算涨跌幅 (%)
        if 'change_pct' not in df.columns and 'change' in df.columns and 'pre_close' in df.columns:
            df['change_pct'] = (df['change'] / df['pre_close'] * 100).fillna(0)
        
        # 盘中收盘价 = 最新价
        if 'close' not in df.columns and 'price' in df.columns:
            df['close'] = df['price']
        
        return df
    
    
# ========== EPIC-002: Financial Data API Schemas ==========

class FinancialIndicatorsResponse(BaseModel):
    """Enhanced Financial Indicators Response Schema"""
    stock_code: str
    report_date: str
    report_type: str = Field(..., description="Q1, Q2, Q3, Annual")
    
    # Income Statement
    revenue: Optional[float] = Field(None, description="营业收入 (亿元)")
    operating_cost: Optional[float] = Field(None, description="营业成本 (亿元)")
    operating_profit: Optional[float] = Field(None, description="营业利润 (亿元)")
    net_profit: Optional[float] = Field(None, description="净利润 (亿元)")
    
    # Balance Sheet
    total_assets: Optional[float] = Field(None, description="总资产 (亿元)")
    net_assets: Optional[float] = Field(None, description="净资产 (亿元)")
    goodwill: Optional[float] = Field(None, description="商誉 (亿元)")
    monetary_funds: Optional[float] = Field(None, description="货币资金 (亿元)")
    interest_bearing_debt: Optional[float] = Field(None, description="有息负债 (亿元)")
    accounts_receivable: Optional[float] = Field(None, description="应收账款 (亿元)")
    inventory: Optional[float] = Field(None, description="存货 (亿元)")
    accounts_payable: Optional[float] = Field(None, description="应付账款 (亿元)")
    
    # Cash Flow
    operating_cash_flow: Optional[float] = Field(None, description="经营性现金流净额 (亿元)")
    
    # Equity
    major_shareholder_pledge_ratio: Optional[float] = Field(None, description="大股东质押率")



class FinancialHistoryResponse(BaseModel):
    """Visual History Response Schema"""
    stock_code: str
    periods: int
    report_type: str
    data: List[FinancialIndicatorsResponse]


# ========== EPIC-002: Market Valuation API Schemas ==========

class ValuationResponse(BaseModel):
    """Real-time Valuation Response Schema"""
    stock_code: str
    report_date: str
    
    # Market Cap Data
    total_market_cap: Optional[float] = Field(None, description="总市值 (亿元)")
    circulating_market_cap: Optional[float] = Field(None, description="流通市值 (亿元)")
    
    # Valuation Ratios
    pe_ttm: Optional[float] = Field(None, description="市盈率 (TTM)")
    pe_static: Optional[float] = Field(None, description="市盈率 (静态)")
    pb_ratio: Optional[float] = Field(None, description="市净率 (PB)")
    ps_ratio: Optional[float] = Field(None, description="市销率 (PS)")
    pcf_ratio: Optional[float] = Field(None, description="市现率 (PCF)")
    dividend_yield_ttm: Optional[float] = Field(None, description="股息率 (TTM)")


class ValuationHistoryResponse(BaseModel):
    """Historical Valuation Response Schema"""
    stock_code: str
    years: int
    frequency: str
    
    # Statistics
    stats: Dict[str, Any] = Field(..., description="统计数据 (mean, median, p25, p50, p75, p90)")
    
    # Time Series Data (Optional for chart)
    dates: List[str]
    pe_ttm_list: List[Optional[float]]
    pb_ratio_list: List[Optional[float]]


class IndustryStatsResponse(BaseModel):
    """Industry Statistics Response"""
    industry_code: str
    industry_name: str
    stock_count: int
    report_date: str
    
    # Valuation Distribution
    pe_ttm_stats: Dict[str, float] = Field(..., description="PE TTM 统计 (mean, median, p25/50/75)")
    pb_ratio_stats: Dict[str, float] = Field(..., description="PB 统计")
    
    # Performance Distribution
    roe_stats: Optional[Dict[str, float]] = Field(None, description="ROE 统计")
    revenue_growth_stats: Optional[Dict[str, float]] = Field(None, description="营收增长率统计")
