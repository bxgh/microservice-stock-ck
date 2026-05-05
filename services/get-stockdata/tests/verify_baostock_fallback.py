
import asyncio
import logging
from data_services.industry_service import IndustryService
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestFallback")

async def test_fallback():
    print("--- Initializing IndustryService ---")
    service = IndustryService()
    await service.initialize()
    
    industry_name = "C15酒、饮料和精制茶制造业" # Baostock verified name
    print(f"--- Fetching Stats for {industry_name} ---")
    
    # This should trigger AkShare -> ProxyError -> Fallback to Baostock
    result = await service.get_industry_stats(industry_name)
    
    print("\n--- Result ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if result and 'pe_ttm_stats' in result and result['stock_count'] > 0:
        print("✅ SUCCESS: Retrieved data (likely via Fallback)")
    else:
        print("❌ FAILED: No data returned")

if __name__ == "__main__":
    asyncio.run(test_fallback())
