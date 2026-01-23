import asyncio
import logging
import aiohttp
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import pytz

from .constants import MOOTDX_TICK_ENDPOINT
from .utils import clean_stock_code

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class TickFetcher:
    """
    Unified Tick Data Fetcher
    
    Supports:
    - Mode.REALTIME: Single fast request (for Intraday Collector)
    - Mode.HISTORICAL: Smart matrix/linear search (for Backfill/History)
    """
    
    class Mode(Enum):
        REALTIME = "realtime"
        HISTORICAL = "historical"
        
    # Search Matrix: (start, offset, description)
    # Used for ensuring data integrity during backfill
    SEARCH_MATRIX = [
        (0, 5000, "Full Base"),
        (3500, 800, "Mid-Morning Gap"),
        (4000, 500, "Late-Morning Gap"),
        (4500, 800, "Early-Afternoon Gap"),
        (3000, 1000, "Deep Probe 1"),
        (5000, 1000, "Deep Probe 2"),
        (6000, 1200, "Deep Probe 3"),
        (2000, 1500, "Wide Scan 1"),
        (7000, 1500, "Wide Scan 2"),
    ]

    TARGET_TIME = "09:25"
    
    def __init__(self, http_session: aiohttp.ClientSession, api_url: str, mode: Mode = Mode.REALTIME):
        """
        Args:
            http_session: aiohttp ClientSession
            api_url: Base URL of mootdx-api (e.g., http://localhost:8003)
            mode: Fetch mode
        """
        self.http = http_session
        self.api_url = api_url.rstrip('/')
        self.mode = mode

    async def fetch(
        self, 
        stock_code: str, 
        trade_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch tick data based on configured mode.
        
        Args:
            stock_code: Stock code (e.g. "600519")
            trade_date: Optional date string "YYYYMMDD". 
                        If None, fetches TODAY's data.
        """
        # 1. Clean stock code (remove prefixes)
        clean_code = self._clean_code(stock_code)
        
        # 2. Determine strategy
        # Even in HISTORICAL mode, if date is today, we might use a lighter strategy or full matrix.
        # But per specs:
        # - REALTIME: Single request
        # - HISTORICAL: Matrix/Linear search
        
        if self.mode == self.Mode.REALTIME:
            return await self._fetch_realtime(clean_code)
        else:
            is_today = (trade_date is None) or (trade_date == datetime.now(CST).strftime("%Y%m%d"))
            if is_today:
                return await self._fetch_historical_matrix(clean_code)
            else:
                return await self._fetch_historical_linear(clean_code, trade_date)

    async def _fetch_realtime(self, code: str) -> List[Dict]:
        """Single request for realtime update"""
        url = self.api_url + MOOTDX_TICK_ENDPOINT.format(code=code)
        try:
            # Short timeout for realtime
            async with self.http.get(url, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                if resp.status == 200:
                    return await resp.json()
                # 404 is expected for market open/not-started stocks
                if resp.status != 404:
                    logger.warning(f"Tick API error {code}: {resp.status}")
        except Exception as e:
            logger.debug(f"Tick fetch failed {code}: {e}")
        return []

    async def _fetch_historical_matrix(self, code: str) -> List[Dict]:
        """Matrix search for today's backfill (ensure completeness)"""
        url = self.api_url + MOOTDX_TICK_ENDPOINT.format(code=code)
        all_frames = []
        
        for start, offset, desc in self.SEARCH_MATRIX:
            try:
                params = {"start": start, "offset": offset}
                async with self.http.get(url, params=params, timeout=12) as resp:
                    if resp.status != 200: continue
                    data = await resp.json()
                    if not data: continue
                    
                    all_frames.append(data)
                    
                    # Gap check: if we hit 09:25, we might be good
                    times = [x.get('time', '') for x in data]
                    if times and min(times) <= self.TARGET_TIME:
                        break
            except Exception as e:
                logger.warning(f"Matrix fetch error {code} [{desc}]: {e}")
                
        return self._merge_and_sort(all_frames)

    async def _fetch_historical_linear(self, code: str, date: str) -> List[Dict]:
        """Linear scan for historical dates"""
        url = self.api_url + MOOTDX_TICK_ENDPOINT.format(code=code)
        all_frames = []
        
        max_depth = 50000
        step = 2000
        current_start = 0
        date_int = int(date)
        
        while current_start < max_depth:
            try:
                params = {"date": date_int, "start": current_start, "offset": step}
                async with self.http.get(url, params=params, timeout=15) as resp:
                    if resp.status != 200: break
                    data = await resp.json()
                    if not data: break
                    
                    all_frames.append(data)
                    
                    # Check if we reached opening time
                    times = [x.get('time', '') for x in data]
                    earliest = min(times) if times else "23:59"
                    
                    if earliest <= self.TARGET_TIME:
                        break
                    
                    current_start += step
            except Exception as e:
                logger.error(f"Linear fetch error {code} date={date}: {e}")
                break
                
        return self._merge_and_sort(all_frames)

    def _merge_and_sort(self, frames: List[List[Dict]]) -> List[Dict]:
        """Merge frames, deduplicate (strict), and sort"""
        if not frames: return []
        
        merged = []
        for f in frames: merged.extend(f)
        
        seen = set()
        final_data = []
        
        # Consistent Deduplication Logic (same as Deduplicator but local to this batch)
        for item in merged:
            vol = item.get('vol', item.get('volume', 0))
            key = (item.get('time'), item.get('price'), vol)
            
            if key not in seen:
                seen.add(key)
                final_data.append(item)
                
        final_data.sort(key=lambda x: x.get('time', ''))
        return final_data

    def _clean_code(self, code: str) -> str:
        """Sanitize stock code: remove sh/sz prefixes and dots"""
        return clean_stock_code(code)
