#!/usr/bin/env python3
"""
Test Manual Monster Stocks Configuration
"""
import sys
sys.path.insert(0, '/app/src')

import asyncio
from services.stock_pool.config_manager import StockPoolConfigManager
from services.stock_pool.hot_sectors_manager import HotSectorsManager

async def main():
    print("="*60)
    print("Testing Manual Monster Stocks Configuration")
    print("="*60)
    
    # Initialize
    config_mgr = StockPoolConfigManager()
    await config_mgr.load_config()
    
    manager = HotSectorsManager(config_mgr)
    
    # 1. Check Config
    print("\n1. Checking Config...")
    config = config_mgr.get_config()
    monster_conf = config["hot_sectors"]["sectors"]["monster"]
    
    print(f"   Name: {monster_conf['name']}")
    print(f"   Dynamic: {monster_conf.get('dynamic')}")
    if "sources" in monster_conf:
        print(f"   Sources: {len(monster_conf['sources'])} items")
        for s in monster_conf['sources']:
            print(f"     - Type: {s['type']}")
            if 'codes' in s:
                print(f"       Codes: {s['codes']}")
    
    # 2. Build Pool
    print("\n2. Building Pool (should include manual monsters)...")
    pool = await manager.get_pool()
    
    print(f"\n   Total Pool Size: {len(pool)}")
    
    # Check if our manual monster stocks are in the pool
    monster_codes = monster_conf["sources"][0]["codes"]
    found_count = 0
    missing = []
    
    for code in monster_codes:
        if code in pool:
            found_count += 1
        else:
            missing.append(code)
            
    print(f"\n   Found {found_count}/{len(monster_codes)} manual monster stocks in pool")
    if missing:
        print(f"   ❌ Missing: {missing}")
    else:
        print(f"   ✅ All manual monster stocks found!")

    return 0

if __name__ == "__main__":
    asyncio.run(main())
