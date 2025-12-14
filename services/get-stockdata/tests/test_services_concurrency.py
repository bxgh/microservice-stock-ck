# -*- coding: utf-8 -*-
"""
Concurrency Tests for EPIC-002/005 Services

Tests thread safety and concurrent access patterns for:
- QuotesService (snapshot cache)
- FinancialService (shared stats)
- ValuationService (shared stats)

Based on code review recommendation: tests/test_mootdx_connection_concurrency.py
"""

import pytest
import asyncio
from typing import List

# Import services to test
from src.data_services.quotes_service import QuotesService
from src.data_services.financial_service import FinancialService
from src.data_services.valuation_service import ValuationService


class TestQuotesServiceConcurrency:
    """Test QuotesService concurrent access patterns"""
    
    @pytest.mark.asyncio
    async def test_concurrent_quote_requests(self):
        """Test concurrent real-time quote requests"""
        service = QuotesService(enable_cache=False)
        await service.initialize()
        
        try:
            codes = ['600519', '000001', '000002']
            
            # Create 50 concurrent requests
            tasks = [service.get_realtime_quotes(codes) for _ in range(50)]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify no exceptions occurred
            for r in results:
                assert not isinstance(r, Exception), f"Request failed: {r}"
                assert isinstance(r, list), "Should return list of quotes"
        
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_snapshot_cache_thread_safety(self):
        """Test snapshot cache update under concurrent access"""
        service = QuotesService(enable_cache=False)
        await service.initialize()
        
        try:
            # Simulate concurrent reads during cache updates
            async def read_snapshot():
                codes = ['600519']
                return await service.get_realtime_quotes(codes)
            
            # 100 concurrent reads
            tasks = [read_snapshot() for _ in range(100)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed without data races
            for r in results:
                assert not isinstance(r, Exception), f"Concurrent read failed: {r}"
        
        finally:
            await service.close()


class TestFinancialServiceConcurrency:
    """Test FinancialService concurrent access patterns"""
    
    @pytest.mark.asyncio
    async def test_concurrent_financial_queries(self):
        """Test concurrent financial data queries"""
        service = FinancialService(enable_cache=False)
        await service.initialize()
        
        try:
            codes = ['600519', '000001', '600036']
            
            # Create concurrent requests for different stocks
            tasks = [service.get_enhanced_indicators(code) for code in codes for _ in range(10)]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all requests completed
            assert all(not isinstance(r, Exception) for r in results), \
                "Some concurrent requests failed"
        
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    async def test_stats_counter_thread_safety(self):
        """Test statistics counters are thread-safe under concurrent updates"""
        service = FinancialService(enable_cache=False)
        await service.initialize()
        
        try:
            # Make many concurrent requests to trigger stat updates
            tasks = [service.get_enhanced_indicators('600519') for _ in range(100)]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Stats should be consistent (no negative values, etc.)
            stats = service._stats
            assert stats['total_requests'] >= 0
            assert stats['akshare_calls'] >= 0
            assert stats['cache_hits'] >= 0
            
        finally:
            await service.close()


class TestValuationServiceConcurrency:
    """Test ValuationService concurrent access patterns"""
    
    @pytest.mark.asyncio
    async def test_concurrent_valuation_queries(self):
        """Test concurrent valuation queries"""
        service = ValuationService(enable_cache=False)
        await service.initialize()
        
        try:
            codes = ['600519', '000001']
            
            # Concurrent current valuation requests
            tasks = [service.get_current_valuation(code) for code in codes for _ in range(20)]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed
            assert all(not isinstance(r, Exception) for r in results)
        
        finally:
            await service.close()


@pytest.mark.asyncio
async def test_cross_service_concurrency():
    """Test concurrent access across multiple services"""
    quotes_svc = QuotesService(enable_cache=False)
    financial_svc = FinancialService(enable_cache=False)
    valuation_svc = ValuationService(enable_cache=False)
    
    await quotes_svc.initialize()
    await financial_svc.initialize()
    await valuation_svc.initialize()
    
    try:
        code = '600519'
        
        # Mix different service calls concurrently
        tasks = []
        for _ in range (10):
            tasks.append(quotes_svc.get_realtime_quotes([code]))
            tasks.append(financial_svc.get_enhanced_indicators(code))
            tasks.append(valuation_svc.get_current_valuation(code))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all succeeded
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"Cross-service concurrency failures: {errors}"
    
    finally:
        await quotes_svc.close()
        await financial_svc.close()
        await valuation_svc.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
