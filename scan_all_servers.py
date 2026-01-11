
import time
import logging
import pandas as pd
from mootdx.quotes import Quotes

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Target to test
SYMBOLS = ['000001', '600000', '600519']
DATES = ['20260109', '20260108']

def get_candidates():
    # User's suggested IP pool + Known Control
    return [
        ('175.6.5.153', 7709, 'User-1'),
        ('139.9.51.18', 7709, 'User-2'),
        ('139.159.239.163', 7709, 'User-3'),
        ('119.147.212.81', 7709, 'User-4'),
        ('124.71.187.122', 7709, 'User-5'),
        ('59.36.5.11', 7709, 'Known-Good')
    ]

def test_server(ip, port, name):
    try:
        client = Quotes.factory(market='std', bestip=False, server=(ip, port), timeout=5)
        for symbol in SYMBOLS:
            for date in DATES:
                try:
                    data = client.transactions(symbol=symbol, date=date)
                    if data is not None and not data.empty:
                        logger.info(f"✅ [{name}] {ip}:{port} | {symbol} | {date} -> SUCCESS ({len(data)} rows)")
                        return True
                except Exception:
                    continue
        logger.info(f"❌ [{name}] {ip}:{port} -> FAILED (No Tick Data)")
        return False
    except Exception as e:
        logger.info(f"🔥 [{name}] {ip}:{port} -> ERROR ({str(e)})")
        return False

if __name__ == "__main__":
    candidates = get_candidates()
    logger.info(f"Starting Scan for {len(candidates)} candidates on Server 41...")
    
    results = []
    for ip, port, name in candidates:
        if test_server(ip, port, name):
            results.append(f"{ip}:{port} ({name})")
            
    logger.info("\n" + "="*30)
    logger.info("WORKING IPS SUMMARY:")
    for res in results:
        logger.info(res)
    logger.info("="*30)
