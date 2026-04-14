"""
Data Source Enums
数据源和数据类型枚举定义
"""
from enum import Enum


class DataSource(str, Enum):
    """
    数据源枚举
    
    定义系统支持的所有数据源标识符
    """
    MOOTDX = "mootdx"               # 通达信直连
    MOOTDX_API = "mootdx-api"       # 通达信 API 代理
    EASYQUOTATION = "easyquotation" # 新浪/腾讯行情
    AKSHARE_API = "akshare-api"     # AkShare API
    BAOSTOCK_API = "baostock-api"   # 证券宝 API
    PYWENCAI_API = "pywencai-api"   # 同花顺问财
    MYSQL = "mysql"                 # 本地 MySQL (基础信息、行业数据)
    CLICKHOUSE = "clickhouse"       # ClickHouse (特征矩阵、分笔存储)
    ERROR = "error"                 # 错误标识


class DataType(str, Enum):
    """
    数据类型枚举
    
    定义系统支持的所有数据类型
    """
    QUOTES = "QUOTES"           # 实时行情
    TICK = "TICK"               # 分笔成交
    HISTORY = "HISTORY"         # 历史K线
    RANKING = "RANKING"         # 排行榜
    SECTOR = "SECTOR"           # 板块数据
    FINANCE = "FINANCE"         # 财务数据
    VALUATION = "VALUATION"     # 估值数据
    INDEX = "INDEX"             # 指数成分
    INDUSTRY = "INDUSTRY"       # 行业数据
    DRAGON_TIGER = "DRAGON_TIGER"  # 龙虎榜
    MARGIN = "MARGIN"              # 融资融券
    
    # 扩展数据类型
    ISSUE_PRICE = "ISSUE_PRICE"     # 发行价
    SW_INDUSTRY = "SW_INDUSTRY"     # 申万行业
    FEATURES = "FEATURES"           # 特征矩阵
    
    # Mootdx 扩展
    STOCK_LIST = "STOCK_LIST"   # 股票列表
    FINANCE_INFO = "FINANCE_INFO"  # 财务基础信息（mootdx）
    XDXR = "XDXR"               # 除权除息
    INDEX_BARS = "INDEX_BARS"   # 指数K线

