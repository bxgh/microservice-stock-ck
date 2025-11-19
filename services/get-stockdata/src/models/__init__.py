"""
数据模型层 - 定义所有数据结构和类型
"""

try:
    from .stock_models import (
        StockInfo,
        StockCodeMapping,
        StockListRequest,
        StockListResponse,
        StockDetailResponse,
        StockSearchRequest,
        StockBatchRequest,
        StockMappingsResponse,
        StockExportRequest,
        CacheStatusResponse,
        StockFilter,
        ExternalStockResponse,
        ExternalStockListResponse,
        StockDataAdapter,
        CacheKeyGenerator
    )
    from .base_models import (
        ApiResponse,
        PaginationInfo
    )

    __all__ = [
        "StockInfo",
        "StockCodeMapping",
        "StockListRequest",
        "StockListResponse",
        "StockDetailResponse",
        "StockSearchRequest",
        "StockBatchRequest",
        "StockMappingsResponse",
        "StockExportRequest",
        "CacheStatusResponse",
        "StockFilter",
        "ExternalStockResponse",
        "ExternalStockListResponse",
        "StockDataAdapter",
        "CacheKeyGenerator",
        "ApiResponse",
        "PaginationInfo"
    ]
except ImportError:
    # 如果模型文件不存在，创建一个空的__all__
    __all__ = []