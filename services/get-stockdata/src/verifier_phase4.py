
import asyncio
import logging
from src.data_services.quotes_service import QuotesService
from src.data_services.cache_manager import CacheManager

logging.basicConfig(level=logging.INFO)

async def verify():
    print("--- Verifying EPIC-005 Phase 4: Batch Quotes ---")
    
    # 1. Initialize Service
    quotes_service = QuotesService(enable_cache=True)
    await quotes_service.initialize()
    
    try:
        # 2. Test Batch Fetch
        codes = ["600519", "000001", "000858"]
        print(f"\nFetching quotes for: {codes}...")
        
        quotes = await quotes_service.get_realtime_quotes(codes)
        
        if quotes:
            print(f"SUCCESS. Got {len(quotes)} quotes.")
            for q in quotes:
                print(f" - {q['code']} {q['name']} Price:{q['price']} Vol:{q['volume']} Cap:{q['market_cap']}")
                
            # Validation
            assert len(quotes) > 0
            if any(q['market_cap'] for q in quotes if q['market_cap']):
                print("✅ Market Cap found.")
            else:
                print("⚠️ Market Cap missing/zero (Market might be closed or field mapping issue).")
        else:
            print("FAILED. No quotes returned.")
            
    finally:
        await quotes_service._cache_manager.close()

if __name__ == "__main__":
    asyncio.run(verify())
