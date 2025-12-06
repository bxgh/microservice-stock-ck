#!/usr/bin/env python3
"""
Integration test for Hot Sectors Manager
Tests with real akshare data to verify ETF codes work
"""
import asyncio
import sys
sys.path.insert(0, '/app/src')

from services.stock_pool.config_manager import StockPoolConfigManager
from services.stock_pool.hot_sectors_manager import HotSectorsManager

async def main():
    print("="*60)
    print("Hot Sectors Manager Integration Test")
    print("="*60)
    
    # Initialize
    config_mgr = StockPoolConfigManager()
    await config_mgr.load_config()
    
    manager = HotSectorsManager(config_mgr)
    
    # Test pool building
    print("\n📊 Building Hot Sectors Pool...")
    try:
        stocks = await manager.get_pool()
        
        print(f"\n✅ Successfully built pool with {len(stocks)} stocks")
        print(f"\n📋 First 10 stocks: {stocks[:10]}")
        print(f"📋 Last 10 stocks: {stocks[-10:]}")
        
        # Verify uniqueness
        unique_count = len(set(stocks))
        print(f"\n🔍 Uniqueness check: {unique_count}/{len(stocks)} unique")
        
        if unique_count != len(stocks):
            print(f"⚠️  Warning: {len(stocks) - unique_count} duplicate codes found")
        
        # Check cache file
        import json
        from pathlib import Path
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        cache_dir = Path("cache/hot_sectors")
        today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
        cache_file = cache_dir / f"hot_sectors_{today}.json"
        
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            print(f"\n💾 Cache file created: {cache_file}")
            print(f"   Updated at: {cache_data.get('updated_at')}")
            print(f"   Stock count: {cache_data.get('count')}")
        
        print("\n✅ Integration test PASSED")
        return 0
        
    except Exception as e:
        print(f"\n❌ Integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
