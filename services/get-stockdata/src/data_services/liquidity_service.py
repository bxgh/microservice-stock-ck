# -*- coding: utf-8 -*-
"""
EPIC-005 Liquidity Service
Provides liquidity metrics for risk control.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import pandas as pd
import akshare as ak

from .quotes_service import QuotesService

logger = logging.getLogger(__name__)

class LiquidityService:
    """Liquidity Data Service
    
    Provides:
    1. Liquidity metrics (turnover, avg volume)
    2. Order book depth (simulated/L1 if available)
    3. Bid-Ask spread analysis
    """
    
    def __init__(self, quotes_service: Optional[QuotesService] = None):
        self._quotes_service = quotes_service
        self._initialized = False
        
    async def initialize(self):
        if self._quotes_service and not self._quotes_service._initialized:
             await self._quotes_service.initialize()
        self._initialized = True
        logger.info("✅ LiquidityService initialized")

    def _get_mock_order_book(self, current_price: float) -> Dict[str, Any]:
        """Generate mock 5-level order book"""
        tick = 0.01 if current_price < 100 else 0.1
        return {
            "bids": [
                {"price": round(current_price - i*tick, 2), "volume": 100*(i+1)} 
                for i in range(1, 6)
            ],
            "asks": [
                {"price": round(current_price + i*tick, 2), "volume": 100*(i+1)} 
                for i in range(1, 6)
            ],
            "timestamp": datetime.now().isoformat(),
            "simulated": True
        }

    async def get_liquidity_metrics(self, stock_code: str) -> Dict[str, Any]:
        """Get liquidity metrics for a stock"""
        
        # 1. Get Realtime Info (Price, Volume, Turnover)
        price = 0.0
        volume = 0
        turnover = 0.0
        
        if self._quotes_service:
            quotes = await self._quotes_service.get_realtime_quotes([stock_code])
            if quotes:
                q = quotes[0]
                price = q.get('price', 0.0) or 0.0
                volume = q.get('volume', 0) or 0
                turnover = q.get('turnover', 0.0) or 0.0
        
        # 2. Calculate Avg Daily Volume (20d) via AkShare History
        # Ideally this should be cached or fetched from a history service.
        # For MVP/Epic-005, we fetch it on demand or use a simple estimate.
        # Fetching 20d history on every liquidity check is slow.
        # We'll mock/estimate it from current volume * ratio or implement a simplified fetch.
        
        # For now, let's try to fetch small history if cheap, or fallback.
        avg_daily_volume = volume # Default to current if fail
        
        try:
            # Quick sync fetch for history (mock logic for now to avoid heavy network io in loop)
            # In production, this data should come from valid historical db
            pass 
        except Exception:
            pass
            
        # 3. Order Book
        order_book = self._get_mock_order_book(price)
        
        # 4. Bid-Ask Spread
        # Estimated from order book
        spread = 0.0
        if order_book['bids'] and order_book['asks']:
             spread = order_book['asks'][0]['price'] - order_book['bids'][0]['price']

        return {
            "stock_code": stock_code,
            "avg_daily_volume": float(avg_daily_volume), # Placeholder
            "avg_turnover_20d": float(turnover), # Placeholder: use current turnover as proxy for now
            "bid_ask_spread": round(spread, 3),
            "order_book_depth_5": order_book,
            "liquidity_score": 85.0 # Mock score
        }
