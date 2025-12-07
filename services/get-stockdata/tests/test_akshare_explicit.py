import os
import akshare as ak
import requests
import logging
import time

# Enable verbose logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

def test_akshare_explicit_proxy():
    proxy_url = "http://127.0.0.1:8118"
    proxies = {"http": proxy_url, "https": proxy_url}
    
    print(f"\n{'='*20} Testing Akshare with Explicit Proxy {'='*20}")
    
    # 1. Set via akshare utility (if available)
    try:
        from akshare.utils.context import set_proxies
        print(f"Setting proxies via set_proxies: {proxies}")
        set_proxies(proxies)
    except ImportError:
        print("Could not import set_proxies")

    # 2. Run test
    try:
        print("  Testing Akshare (Library Call)...")
        df = ak.stock_zh_a_spot_em()
        print(f"✅ OK ({len(df)} rows)")
    except Exception as e:
        print(f"❌ Failed: {str(e)[:100]}...")

if __name__ == "__main__":
    test_akshare_explicit_proxy()
