# -*- coding: utf-8 -*-
"""
EPIC-007 数据服务标准化 Schema 定义

定义各类数据的标准字段格式，确保不同数据源返回的数据格式一致。

@author: EPIC-007 Story 007.02
@date: 2025-12-06
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
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


# 为 Story 007.02b (TickService) 预留
@dataclass
class TickSchema:
    """分笔成交标准字段定义（预留）
    
    用于 Story 007.02b TickService。
    """
    code: str
    time: str  # HH:MM:SS
    price: float
    volume: int  # 手
    amount: float  # 元
    direction: str  # B/S/N (买/卖/中性)
    timestamp: datetime = field(default_factory=datetime.now)


# 为 Story 007.03 (RankingService) 预留
@dataclass
class RankingSchema:
    """榜单数据标准字段定义（预留）
    
    用于 Story 007.03 RankingService。
    """
    rank: int
    code: str
    name: str
    change_pct: float
    price: float
    volume: float
    amount: float
    timestamp: datetime = field(default_factory=datetime.now)


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
