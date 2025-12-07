#!/usr/bin/env python3
"""
Test Monster Stocks fetching with retry mechanism
"""
import sys
sys.path.insert(0, '/app/src')

import asyncio
from services.stock_pool.config_manager import StockPoolConfigManager
from services.stock_pool.hot_sectors_manager import HotSectorsManager

async def main():
    print("="*60)
    print("Testing Monster Stocks with Retry Mechanism")
    print("="*60)
    
    # Initialize
    config_mgr = StockPoolConfigManager()
    await config_mgr.load_config()
    
    config = config_mgr.get_config()
    monster_config = config.get("hot_sectors", {}).get("sectors", {}).get("monster", {})
    
    if not monster_config:
        print("❌ Monster stocks config not found")
        return 1
    
    print(f"\n📋 Monster Stocks Config:")
    print(f"   Size: {monster_config.get('size')}")
    print(f"   Criteria: {monster_config.get('criteria')}")
    
    manager = HotSectorsManager(config_mgr)
    
    print(f"\n🎲 Fetching monster stocks (with 3 retries)...")
    try:
        stocks = await manager._get_monster_stocks(monster_config)
        
        if stocks:
            print(f"\n✅ Success! Got {len(stocks)} monster stocks:")
            for i, code in enumerate(stocks, 1):
                print(f"   {i}. {code}")
        else:
            print(f"\n⚠️  No monster stocks found (may have failed)")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
