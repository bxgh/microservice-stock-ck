#!/usr/bin/env python3
"""
Direct test of updated ETF fetching logic
"""
import sys
sys.path.insert(0, '/app/src')

import asyncio
from services.stock_pool.config_manager import StockPoolConfigManager
from services.stock_pool.hot_sectors_manager import HotSectorsManager

async def main():
    print("="*60)
    print("Testing Updated ETF Fetching Logic")
    print("="*60)
    
    # Initialize
    config_mgr = StockPoolConfigManager()
    await config_mgr.load_config()
    
    manager = HotSectorsManager(config_mgr)
    
    # Test individual ETF fetch
    test_etf = "512760"  # 芯片ETF
    print(f"\n🧪 Testing single ETF: {test_etf}")
    
    try:
        # Call the sync method in thread (same as real usage)
        stocks = await asyncio.to_thread(manager._get_etf_stocks_sync, test_etf, 10)
        
        if stocks:
            print(f"✅ Got {len(stocks)} stocks from ETF {test_etf}:")
            for i, code in enumerate(stocks, 1):
                print(f"   {i}. {code}")
        else:
            print(f"❌ No stocks returned from ETF {test_etf}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Now test full pool build (without cache)
    print(f"\n{'='*60}")
    print("Testing Full Pool Build (deleting cache first)")
    print(f"{'='*60}")
    
    # Delete cache
    import shutil
    from pathlib import Path
    cache_dir = Path("cache/hot_sectors")
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        print("🗑️  Deleted cache directory")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Build fresh pool
    try:
        pool = await manager._build_pool()
        print(f"\n✅ Built pool with {len(pool)} stocks")
        print(f"\n📋 First 20 stocks: {pool[:20]}")
        print(f"📋 Last 10 stocks: {pool[-10:]}")
        
        # Show breakdown by uniqueness
        unique = len(set(pool))
        print(f"\n🔍 Uniqueness: {unique}/{len(pool)} unique stocks")
        
    except Exception as e:
        print(f"❌ Error building pool: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
