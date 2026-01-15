
import asyncio
import os
import logging
from core.sync_service import KLineSyncService

logging.basicConfig(level=logging.INFO)

async def test_kline_filtering():
    service = KLineSyncService()
    # Mock Redis connection (or use real one if available)
    # Since we are running in docker, it should use real one
    
    print("\n--- Testing KLineSyncService Filtering ---")
    try:
        # Get codes using the internal method which should now filter
        codes = await service._get_stock_codes_from_redis()
        
        print(f"Total codes retrieved after filtering: {len(codes)}")
        
        # Check if some non-A-shares are present (they shouldn't be)
        # BSE codes usually start with 8 or 4
        bse_codes = [c for c in codes if c.startswith(('8', '4'))]
        # B-shares usually start with 9 or 2 (for A-share standard)
        b_shares = [c for c in codes if c.startswith(('900', '200'))]
        
        print(f"BSE codes found: {len(bse_codes)}")
        print(f"B-shares found: {len(b_shares)}")
        
        if len(bse_codes) == 0 and len(b_shares) == 0:
            print("✅ SUCCESS: Internal filtering works. No BSE or B-shares in the target list.")
        else:
            print("❌ FAILURE: Non-A-shares found in filtered list.")
            if bse_codes: print(f"Sample BSE: {bse_codes[:5]}")
            if b_shares: print(f"Sample B: {b_shares[:5]}")
            
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_kline_filtering())
