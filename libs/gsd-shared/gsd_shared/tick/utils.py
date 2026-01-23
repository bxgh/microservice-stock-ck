def clean_stock_code(code: str) -> str:
    """
    Sanitize stock code: remove sh/sz prefixes and dots
    """
    if not code: return ""
    return code.lower().lstrip('sh').lstrip('sz').lstrip('.')
