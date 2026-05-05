
import asyncio
import logging
from src.data_services.quotes_service import QuotesService
from src.data_services.liquidity_service import LiquidityService

async def verify_liquidity():
    print("--- Verifying EPIC-005 Phase 5: Liquidity API ---")
    
    # 1. Init Services
    quotes_service = QuotesService(enable_cache=True)
    await quotes_service.initialize()
    
    liquidity_service = LiquidityService(quotes_service)
    await liquidity_service.initialize()
    
    try:
        stock_code = "600519"
        print(f"Fetching liquidity for {stock_code}...")
        
        metrics = await liquidity_service.get_liquidity_metrics(stock_code)
        
        print("Result:")
        print(metrics)
        
        # Validation
        assert metrics['stock_code'] == stock_code
        assert 'avg_daily_volume' in metrics
        assert 'bid_ask_spread' in metrics
        assert 'order_book_depth_5' in metrics
        
        ob = metrics['order_book_depth_5']
        assert 'bids' in ob
        assert 'asks' in ob
        assert len(ob['bids']) == 5
        
        print("✅ Liquidity Metrics Verified")
            
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        
    await quotes_service._cache_manager.close()

if __name__ == "__main__":
    asyncio.run(verify_liquidity())
