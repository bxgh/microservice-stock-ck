import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core.tdx_pool import TDXClientPool

async def run_verification():
    print("🚀 Starting TDXClientPool Concurrency Verification...")
    pool = TDXClientPool(size=3)
    
    # Mock Quotes.factory
    with patch('core.tdx_pool.Quotes.factory') as mock_factory:
        clients_created = []
        def side_effect(**kwargs):
            m = MagicMock()
            clients_created.append(m)
            return m
        mock_factory.side_effect = side_effect
        
        # 1. Test Initialization
        await pool.initialize()
        if pool.active_count == 3:
            print("✅ Initialization: Success (count=3)")
        else:
            print(f"❌ Initialization: Failed (count={pool.active_count})")
            return
            
        # 2. Test Round Robin
        results = []
        for _ in range(6):
            results.append(id(await pool.get_next()))
            
        # Expected: id0, id1, id2, id0, id1, id2
        if results[0] == results[3] and results[1] == results[4] and results[2] == results[5]:
            print("✅ Round-Robin Logic: Success")
        else:
            print(f"❌ Round-Robin Logic: Failed (results={results})")
            
        # 3. Test Concurrency
        async def worker():
            c = await pool.get_next()
            return id(c)
            
        tasks = [worker() for _ in range(30)]
        concurrent_results = await asyncio.gather(*tasks)
        
        counts = {}
        for rid in concurrent_results:
            counts[rid] = counts.get(rid, 0) + 1
            
        # Each client should be used exactly 10 times (30 / 3)
        if all(c == 10 for c in counts.values()):
            print("✅ Concurrency Balance: Success (10 hits each)")
        else:
            print(f"❌ Concurrency Balance: Failed (counts={counts})")

if __name__ == "__main__":
    asyncio.run(run_verification())
