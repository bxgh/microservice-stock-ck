"""
股票代码验证工具模块

提供 A 股代码合法性校验等通用验证函数
"""


def is_valid_a_stock(code: str, include_bj: bool = True) -> bool:
    """
    判断是否为有效的 A 股代码 (含北京交易所)
    
    过滤规则:
    - 沪深主板/创业板/科创板
    - 北京交易所 (43, 83, 87, 88, 92 开头)
    
    Args:
        code: 6位股票代码字符串 或 9位 TS 格式
        include_bj: 是否包含北交所
        
    Returns:
        bool: True 表示是有效的代码
    """
    if len(code) == 9 and '.' in code:
        code = code.split('.')[0]

    if not code or not isinstance(code, str) or len(code) != 6:
        return False
    
    # 沪深市场
    if code.startswith(('600', '601', '603', '605', '688', '000', '001', '002', '003', '300', '301')):
        return True
    
    # 北交所
    if include_bj and code.startswith(('43', '83', '87', '88', '92')): 
        return True
        
    return False

def is_valid_etf(code: str) -> bool:
    """
    判断是否为有效的 ETF 代码
    
    规则:
    - 51, 56, 58 (沪市)
    - 159, 180 (深市)
    """
    if len(code) == 9 and '.' in code:
        code = code.split('.')[0]
    return code.startswith(('51', '56', '58', '159', '180'))

def is_valid_index(code: str) -> bool:
    """
    判断是否为有效的指数代码
    
    规则:
    - 000 (上证)
    - 399 (深证)
    - 899 (北证)
    """
    if len(code) == 9 and '.' in code:
        code = code.split('.')[0]
    return code.startswith(('000', '399', '899'))
