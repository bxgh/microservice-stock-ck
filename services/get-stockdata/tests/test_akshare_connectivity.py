import os
import akshare as ak
import requests
import logging
import time
import socket
import pytest

# Enable verbose logging for requests/urllib3
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.mark.parametrize("proxy_url", [
    os.getenv("PROXY_URL", "http://192.168.151.18:3128"),
    None,  # Also test without explicit proxy (relying on env)
])
def test_connectivity(proxy_url):
    print(f"\n{'='*20} Testing Proxy: {proxy_url} {'='*20}")
    
    # Check if PROXY_URL is set in env
    current_proxy = os.getenv("HTTP_PROXY")
    print(f"Current Environment Proxy: {current_proxy}")
    
    if proxy_url:
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
    else:
        # Use whatever is in environment
        proxies = None
    
    # 1. EastMoney (Direct Request)
    target_url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
    
    print("  Testing EastMoney (Direct Request)...", end=" ", flush=True)
    try:
        resp = requests.get(target_url, proxies=proxies, timeout=10)
        assert resp.status_code == 200, f"EastMoney API returned {resp.status_code}"
        print(f"✅ OK ({resp.status_code})")
    except Exception as e:
        print(f"❌ Failed: {str(e)[:100]}...")
        # Fail the test if connection fails
        pytest.fail(f"EastMoney connectivity failed: {e}")

    # 2. Akshare (Library Call)
    print("  Testing Akshare (Library Call)...", end=" ", flush=True)
    try:
        # NOTE: Akshare might use its own internal proxy logic or respect os.environ
        # Since we are already running in an env with HTTP_PROXY set by entrypoint.sh,
        # we don't strictly need to overwrite it unless we are testing a specific proxy_url different from env.
        
        # Test a lightweight function
        # stock_zh_a_spot_em() fetches a large list. 
        # index_stock_cons(symbol="000300") is lighter but still hits network.
        df = ak.index_stock_cons(symbol="000300")
        assert df is not None and not df.empty, "Akshare returned empty data"
        print(f"✅ OK ({len(df)} rows)")
    except Exception as e:
        print(f"❌ Failed: {str(e)[:100]}...")
        pytest.fail(f"Akshare connectivity failed: {e}")

if __name__ == "__main__":
    # Allow running as script too
    test_connectivity(os.getenv("PROXY_URL"))
