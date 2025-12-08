import asyncio
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VERIFY")

# Add src to path
sys.path.insert(0, "/app/src")

from data_sources.providers.mootdx_provider import MootdxProvider
from data_sources.providers.akshare_provider import AkshareProvider
from data_sources.providers.easyquotation_provider import EasyquotationProvider
from data_sources.providers.pywencai_provider import PywencaiProvider
from data_sources.providers.base import DataType

async def verify_source(name, provider_cls):
    logger.info(f"STARTING VERIFICATION FOR: {name}")
    try:
        provider = provider_cls()
        await provider.initialize()
        
        # Determine test type based on capabilities
        # Akshare doesn't support QUOTES, use RANKING
        test_type = DataType.QUOTES
        test_kwargs = {"codes": ["600519"]}
        
        if name == "Akshare":
            test_type = DataType.RANKING
            # ranking_type="hot" needs no code
            test_kwargs = {"ranking_type": "hot"}
            logger.info(f"[{name}] Fetching Hot Rank (RANKING)...")
        elif name == "PyWencai":
            test_type = DataType.SCREENING
            test_kwargs = {"query": "贵州茅台股价", "perpage": 1}
            logger.info(f"[{name}] Querying '贵州茅台股价' (SCREENING)...")
        else:
             logger.info(f"[{name}] Fetching snapshot for 600519 (Moutai)...")

        # Standardized fetch call
        result = await provider.fetch(test_type, **test_kwargs)
        
        if result and result.success and result.data is not None and len(result.data) > 0:
            logger.info(f"✅ [{name}] SUCCESS: Got {len(result.data)} records")
            logger.info(f"    Sample: {result.data.iloc[0].to_dict()}")
        else:
            logger.error(f"❌ [{name}] FAILED: {result.error if result else 'Empty result'}")
            
        await provider.close()
        return result.success if result else False
    except Exception as e:
        logger.error(f"❌ [{name}] EXCEPTION: {e}")
        return False

async def main():
    results = {}
    
    # 1. Mootdx
    results['Mootdx'] = await verify_source("Mootdx", MootdxProvider)
    
    # 2. Akshare
    results['Akshare'] = await verify_source("Akshare", AkshareProvider)
    
    # 3. EasyQuotation
    results['EasyQuotation'] = await verify_source("EasyQuotation", EasyquotationProvider)
    
    # 4. PyWencai
    results['PyWencai'] = await verify_source("PyWencai", PywencaiProvider)
    
    logger.info("="*30)
    logger.info("FINAL RESULTS:")
    all_passed = True
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{name}: {status}")
        if not success:
            all_passed = False
    
    if all_passed:
        logger.info("🎉 ALL SYSTEMS GO!")
        sys.exit(0)
    else:
        logger.error("⚠️ SOME CHECKS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
