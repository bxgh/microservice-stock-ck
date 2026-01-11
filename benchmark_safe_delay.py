
import time
import sys
import logging
from mootdx.quotes import Quotes

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Stocks that are known to fail if rate limited (Volume Heavy / Popular?)
PROBLEM_STOCKS = ['000001', '000333', '000538', '000895', '002001', '002179', '600519', '600036']
SERVER = ('59.36.5.11', 7709)
DATE = '20260109'

def test_interval(interval):
    logger.info(f"=== Testing Interval: {interval}s ===")
    client = Quotes.factory(market='std', bestip=False, server=SERVER)
    
    success = 0
    total_records = 0
    start_time = time.time()
    
    for i, symbol in enumerate(PROBLEM_STOCKS):
        iter_start = time.time()
        
        try:
            data = client.transactions(symbol=symbol, date=DATE)
            if data is not None and not data.empty:
                logger.info(f"✅ {symbol}: {len(data)} rows")
                success += 1
                total_records += len(data)
            else:
                logger.warning(f"❌ {symbol}: No Data (Possible Rate Limit)")
        except Exception as e:
            logger.error(f"❌ {symbol}: Error {e}")
            
        # Pacing: Sleep only the remainder of the interval
        elapsed = time.time() - iter_start
        sleep_time = max(0, interval - elapsed)
        time.sleep(sleep_time)
        
    duration = time.time() - start_time
    logger.info(f"Result: {success}/{len(PROBLEM_STOCKS)} Success. Total Time: {duration:.2f}s")
    return success == len(PROBLEM_STOCKS)

if __name__ == "__main__":
    # Binary Search / Step Down
    intervals = [1.2, 1.0, 0.8, 0.5]
    
    best_interval = 1.5
    
    for interval in intervals:
        if test_interval(interval):
            best_interval = interval
            logger.info(f"🎉 Interval {interval}s PASSED!")
        else:
            logger.error(f"💀 Interval {interval}s FAILED!")
            break # Stop if we fail, we found the limit
            
    logger.info(f"🏆 Optimal Safe Interval: {best_interval}s")
