# -*- coding: utf-8 -*-
"""
EPIC-007 数据服务层模块

提供统一的数据服务接口，支持多数据源降级、智能缓存和字段标准化。

核心服务:
- QuotesService: 实时行情服务
- TickService: 分笔成交服务 (Story 007.02b)
- HistoryService: 历史K线服务 (Story 007.04)
- RankingService: 榜单数据服务 (Story 007.03)

使用示例:
    from src.data_services import QuotesService
    
    service = QuotesService()
    await service.initialize()
    
    # 获取行情
    df = await service.get_quotes(['000001', '600519'])
    
    # 涨停股票
    limit_up = await service.get_limit_up_stocks()
    
    await service.close()

@author: EPIC-007
@date: 2025-12-06
"""

# 核心服务
from .quotes_service import QuotesService

# 基础组件
from .cache_manager import (
    CacheManager,
    CacheTTLStrategy,
    TradingAwareTTL,
    FixedTTL,
)

from .schemas import (
    QuoteSchema,
    QuoteWithOrderbookSchema,
    TickSchema,
    RankingSchema,
    FieldMapper,
)

__all__ = [
    # 服务
    'QuotesService',
    
    # 缓存
    'CacheManager',
    'CacheTTLStrategy',
    'TradingAwareTTL',
    'FixedTTL',
    
    # Schema
    'QuoteSchema',
    'QuoteWithOrderbookSchema',
    'TickSchema',
    'RankingSchema',
    'FieldMapper',
]
