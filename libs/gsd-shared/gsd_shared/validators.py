"""
股票代码验证工具模块

提供 A 股代码合法性校验等通用验证函数
"""


def is_valid_a_stock(code: str) -> bool:
    """
    判断是否为有效的 A 股代码 (沪深主板/创业板/科创板)
    
    过滤规则:
    - 沪市 A 股: 600, 601, 603, 605
    - 科创板: 688
    - 深市 A 股: 000, 001, 002, 003
    - 创业板: 300, 301
    
    Args:
        code: 6位股票代码字符串
        
    Returns:
        bool: True 表示是有效的 A 股代码
        
    Examples:
        >>> is_valid_a_stock("600519")
        True
        >>> is_valid_a_stock("000001")
        True
        >>> is_valid_a_stock("200001")  # B股
        False
        >>> is_valid_a_stock("abc123")
        False
    """
    if not code or not isinstance(code, str) or len(code) != 6:
        return False
    
    # 沪市
    if code.startswith(('600', '601', '603', '605', '688')):
        return True
        
    # 深市
    if code.startswith(('000', '001', '002', '003', '300', '301')):
        return True
        
    return False
