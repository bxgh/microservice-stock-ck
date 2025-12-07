# -*- coding: utf-8 -*-
"""
EPIC-007 数据服务层模块

提供统一的数据服务接口，支持多数据源降级、智能缓存和字段标准化。

核心服务:
- QuotesService: 实时行情服务
- TickService: 分笔成交服务 (Story 007.02b)
- HistoryService: 历史K线服务 (Story 007.04)
- RankingService: 榜单数据服务 (Story 007.03)
- IndexService: 指数与ETF服务 (Story 007.05)

@author: EPIC-007
@date: 2025-12-06
"""

from .quotes_service import QuotesService
from .tick_service import TickService
from .ranking_service import RankingService
from .history_service import HistoryService, AdjustType, Frequency
from .index_service import IndexService
from .cache_manager import CacheManager, TradingAwareTTL
from .schemas import (
    QuoteSchema,
    QuoteWithOrderbookSchema,
    TickSchema,
    CapitalFlowResult,
    RankingSchema,
    RankingItem,
    LimitUpItem,
    DragonTigerItem,
    AnomalyType,
    FieldMapper,
)
from .tick_analyzer import TickAnalyzer
from .market_utils import (
    is_st_stock,
    get_board_type,
    get_price_limit,
    is_limit_up,
    is_limit_down,
    calculate_change_pct,
    validate_price_change,
)

__all__ = [
    # Services
    'QuotesService',
    'TickService',
    'RankingService',
    'HistoryService',
    'IndexService',
    
    # History Types
    'AdjustType',
    'Frequency',
    
    # Components
    'CacheManager',
    'TradingAwareTTL',
    'TickAnalyzer',
    
    # Market Utils
    'is_st_stock',
    'get_board_type',
    'get_price_limit',
    'is_limit_up',
    'is_limit_down',
    'calculate_change_pct',
    'validate_price_change',
    
    # Schemas
    'QuoteSchema',
    'QuoteWithOrderbookSchema',
    'TickSchema',
    'CapitalFlowResult',
    'RankingSchema',
    'RankingItem',
    'LimitUpItem',
    'DragonTigerItem',
    'AnomalyType',
    'FieldMapper',
]



