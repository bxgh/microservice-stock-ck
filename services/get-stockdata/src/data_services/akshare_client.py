
# -*- coding: utf-8 -*-
"""
AkShare API Client with Resilience Patterns.

Provides:
1. Retry logic with exponential backoff
2. Circuit Breaker to prevent cascading failures
3. Standardized error handling
"""

import asyncio
import logging
import time
from typing import Any, Optional, Callable
import pandas as pd

try:
    from api.routers.metrics import record_data_source_request, record_circuit_breaker_state
except ImportError:
    def record_data_source_request(source, success, duration): pass
    def record_circuit_breaker_state(source, state): pass

logger = logging.getLogger(__name__)

class AkShareError(Exception):
    """Base exception for AkShare errors"""
    pass

class AkShareTimeoutError(AkShareError):
    """Timeout error"""
    pass

class AkShareNetworkError(AkShareError):
    """Network connection error"""
    pass

class CircuitBreakerOpenError(AkShareError):
    """Circuit breaker is open"""
    pass

class AkShareClient:
    """Robust Client for AkShare"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self._timeout = timeout
        self._max_retries = max_retries
        
        # Circuit Breaker Config
        self._failure_count = 0
        self._failure_threshold = 5
        self._reset_timeout = 60  # seconds
        self._last_failure_time = 0
        self._circuit_open = False
        
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize resources if needed"""
        pass

    async def call(self, func_name: str, **kwargs) -> Optional[pd.DataFrame]:
        """Call AkShare function with retry and circuit breaker"""
        
        # 1. Check Circuit Breaker
        if self._circuit_open:
            if time.time() - self._last_failure_time > self._reset_timeout:
                await self._close_circuit()
            else:
                logger.warning(f"AkShare Circuit Breaker is OPEN. Skipping {func_name}")
                raise CircuitBreakerOpenError(f"AkShare circuit is open. Retry after {self._reset_timeout}s")

        import akshare as ak
        if not hasattr(ak, func_name):
             raise ValueError(f"AkShare has no function named '{func_name}'")
        func = getattr(ak, func_name)

        last_error = None
        start_time = time.time()
        success = False
        
        try:
            for attempt in range(self._max_retries + 1):
                try:
                    loop = asyncio.get_event_loop()
                    # Run sync function in thread pool
                    df = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: func(**kwargs)),
                        timeout=self._timeout
                    )
                    
                    await self._record_success()
                    success = True
                    return df
                    
                except asyncio.TimeoutError:
                    error_msg = f"Timeout ({self._timeout}s)"
                    logger.warning(f"AkShare call '{func_name}' attempt {attempt+1} failed: {error_msg}")
                    last_error = AkShareTimeoutError(error_msg)
                    
                except Exception as e:
                    error_msg = str(e)
                    # Catch specific network errors if possible (e.g. requests.exceptions)
                    logger.warning(f"AkShare call '{func_name}' attempt {attempt+1} failed: {error_msg}")
                    last_error = AkShareNetworkError(error_msg)
                
                # Retry logic
                if attempt < self._max_retries:
                    # Exponential backoff: 1s, 2s, 4s...
                    sleep_time = 2 ** attempt
                    await asyncio.sleep(sleep_time)
                else:
                    await self._record_failure()
            
            # Failed after retries
            logger.error(f"AkShare call '{func_name}' failed after {self._max_retries} retries.")
            if last_error:
                raise last_error
            return None
        finally:
            duration = time.time() - start_time
            record_data_source_request(f"akshare_local_{func_name}", success, duration)

    async def _record_failure(self):
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self._failure_threshold:
                if not self._circuit_open:
                    logger.critical(f"AkShare Circuit Breaker OPENED after {self._failure_count} failures")
                    self._circuit_open = True
                    record_circuit_breaker_state("akshare_local", "open")

    async def _record_success(self):
        async with self._lock:
            if self._failure_count > 0:
                self._failure_count = 0
            if self._circuit_open:
                logger.info("AkShare Circuit Breaker CLOSED")
                self._circuit_open = False
                record_circuit_breaker_state("akshare_local", "closed")
            
    async def _close_circuit(self):
         async with self._lock:
            self._circuit_open = False
            self._failure_count = 0
            logger.info("AkShare Circuit Breaker RESET (Half-Open)")

# Global instance
akshare_client = AkShareClient()
