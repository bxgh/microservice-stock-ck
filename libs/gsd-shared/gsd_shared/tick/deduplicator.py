from collections import deque
from typing import Dict, Any

class TickDeduplicator:
    """
    Unified Tick Deduplicator
    
    Strategy: Tuple-based deduplication (time, price, volume)
    Note: Ideally instances should be scoped per-worker or per-execution context.
          If shared across async tasks for the SAME stock code, external locking might be needed,
          but for standard deque/dict operations in asyncio (single thread), it acts atomically.
    """
    
    def __init__(self, cache_size: int = 1500):
        self.cache: Dict[str, deque] = {}
        self.cache_size = cache_size
        
    def is_duplicate(self, code: str, item: Dict[str, Any]) -> bool:
        """
        Check if a tick item is a duplicate.
        
        Args:
            code: Stock code (e.g. "600519")
            item: Tick item dict from API
            
        Returns:
            True if duplicate, False otherwise.
        """
        key = self._make_key(item)
        
        if code not in self.cache:
            self.cache[code] = deque(maxlen=self.cache_size)
            
        if key in self.cache[code]:
            return True
            
        self.cache[code].append(key)
        return False
    
    def _make_key(self, item: Dict[str, Any]) -> str:
        """
        Generate deduplication key.
        Format: "time|price|vol"
        """
        # Handle field alias: volume vs vol, type vs buyorsell
        vol = item.get('vol', item.get('volume', 0))
        direction = item.get('type', item.get('buyorsell', 'NEUTRAL'))
        return f"{item.get('time')}|{item.get('price')}|{vol}|{direction}"

    def clear(self, code: str = None):
        """Clear cache for a specific code or all codes"""
        if code:
            if code in self.cache:
                del self.cache[code]
        else:
            self.cache.clear()
