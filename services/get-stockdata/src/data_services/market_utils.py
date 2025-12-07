# -*- coding: utf-8 -*-
"""
A股市场工具函数

提供ST股票识别、涨跌幅限制、交易日判断等通用功能。

@author: EPIC-007
@date: 2025-12-07
"""

from typing import Literal
from datetime import datetime


# ST股票名称前缀
ST_PREFIXES = ('ST', '*ST', 'S*ST', 'SST', 'S')

# 涨跌幅限制
PRICE_LIMITS = {
    'normal': 0.10,      # 普通股票 ±10%
    'st': 0.05,          # ST股票 ±5%
    'kcb': 0.20,         # 科创板 ±20%
    'cyb_new': 0.20,     # 创业板(注册制) ±20%
    'bse': 0.30,         # 北交所 ±30%
}


def is_st_stock(name: str) -> bool:
    """检查是否为ST股票
    
    Args:
        name: 股票名称 (如 "ST国华", "*ST中安")
        
    Returns:
        bool: 是否为ST股票
        
    Example:
        >>> is_st_stock("ST国华")
        True
        >>> is_st_stock("贵州茅台")
        False
    """
    if not name:
        return False
    
    # 去除空格
    name = name.strip()
    
    # 检查前缀
    for prefix in ST_PREFIXES:
        if name.startswith(prefix):
            return True
    
    return False


def get_board_type(code: str) -> Literal['main', 'kcb', 'cyb', 'bse']:
    """获取股票所属板块
    
    Args:
        code: 股票代码 (6位)
        
    Returns:
        板块类型: 'main'=主板, 'kcb'=科创板, 'cyb'=创业板, 'bse'=北交所
    """
    code = code.replace('sh', '').replace('sz', '').replace('.', '').zfill(6)
    
    if code.startswith('688'):
        return 'kcb'  # 科创板
    elif code.startswith('3'):
        return 'cyb'  # 创业板
    elif code.startswith(('82', '83', '87', '88', '43', '92')):
        return 'bse'  # 北交所
    else:
        return 'main'  # 主板


def get_price_limit(code: str, name: str = '') -> float:
    """获取股票涨跌幅限制
    
    Args:
        code: 股票代码
        name: 股票名称 (用于ST判断)
        
    Returns:
        float: 涨跌幅限制 (如 0.10 表示 ±10%)
        
    Example:
        >>> get_price_limit('600519', '贵州茅台')
        0.10
        >>> get_price_limit('000001', 'ST国华')
        0.05
        >>> get_price_limit('688001', '华兴源创')
        0.20
    """
    board = get_board_type(code)
    
    # 北交所
    if board == 'bse':
        return PRICE_LIMITS['bse']
    
    # 科创板/创业板
    if board in ('kcb', 'cyb'):
        return PRICE_LIMITS['kcb']
    
    # 主板: 判断是否ST
    if is_st_stock(name):
        return PRICE_LIMITS['st']
    
    return PRICE_LIMITS['normal']


def is_limit_up(price: float, prev_close: float, code: str, name: str = '') -> bool:
    """判断是否涨停
    
    Args:
        price: 当前价格
        prev_close: 昨收价
        code: 股票代码
        name: 股票名称
        
    Returns:
        bool: 是否涨停
    """
    if prev_close <= 0:
        return False
    
    limit = get_price_limit(code, name)
    limit_up_price = round(prev_close * (1 + limit), 2)
    
    return price >= limit_up_price


def is_limit_down(price: float, prev_close: float, code: str, name: str = '') -> bool:
    """判断是否跌停
    
    Args:
        price: 当前价格
        prev_close: 昨收价
        code: 股票代码
        name: 股票名称
        
    Returns:
        bool: 是否跌停
    """
    if prev_close <= 0:
        return False
    
    limit = get_price_limit(code, name)
    limit_down_price = round(prev_close * (1 - limit), 2)
    
    return price <= limit_down_price


def calculate_change_pct(price: float, prev_close: float) -> float:
    """计算涨跌幅
    
    Args:
        price: 当前价格
        prev_close: 昨收价
        
    Returns:
        float: 涨跌幅 (百分比, 如 5.0 表示上涨5%)
    """
    if prev_close <= 0:
        return 0.0
    
    return round((price / prev_close - 1) * 100, 2)


def validate_price_change(
    price: float, 
    prev_close: float, 
    code: str, 
    name: str = ''
) -> bool:
    """验证价格变动是否在合理范围内
    
    用于数据质量检查，检测异常数据
    
    Args:
        price: 当前价格
        prev_close: 昨收价
        code: 股票代码
        name: 股票名称
        
    Returns:
        bool: 价格变动是否合理
    """
    if prev_close <= 0 or price <= 0:
        return False
    
    limit = get_price_limit(code, name)
    change_pct = abs(price / prev_close - 1)
    
    # 允许少量误差 (0.1%)
    return change_pct <= limit + 0.001
