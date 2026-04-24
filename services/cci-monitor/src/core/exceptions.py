from typing import Any, Dict, Optional

class CCIMonitorError(Exception):
    """CCI Monitor 基础异常类"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

class DataSourceError(CCIMonitorError):
    """数据源获取异常"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="DATA_SOURCE_ERROR", details=details)

class DataSourceEmptyError(DataSourceError):
    """数据源返回空数据"""
    def __init__(self, symbol: str):
        super().__init__(f"No data returned for symbol: {symbol}", details={"symbol": symbol})

class DataSourceTimeoutError(DataSourceError):
    """数据源请求超时"""
    def __init__(self, url: str):
        super().__init__(f"Request timeout for URL: {url}", details={"url": url})

class CalculationError(CCIMonitorError):
    """CCI 指标计算异常"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="CALCULATION_ERROR", details=details)

class ConfigurationError(CCIMonitorError):
    """配置项错误"""
    def __init__(self, message: str):
        super().__init__(message, code="CONFIG_ERROR")

class DatabaseError(CCIMonitorError):
    """数据库操作异常"""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        details = {"original_error": str(original_error)} if original_error else {}
        super().__init__(message, code="DATABASE_ERROR", details=details)
