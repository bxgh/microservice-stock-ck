import os
import akshare as ak
import requests
import logging
import functools

# Enable verbose logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Monkey patch requests.Session.request to log details
original_request = requests.Session.request

@functools.wraps(original_request)
def patched_request(self, method, url, *args, **kwargs):
    print(f"\n[DEBUG] Request: {method} {url}")
    print(f"[DEBUG] Proxies: {kwargs.get('proxies')}")
    print(f"[DEBUG] Headers: {kwargs.get('headers')}")
    
    # Check environment variables
    print(f"[DEBUG] Env HTTP_PROXY: {os.environ.get('HTTP_PROXY')}")
    print(f"[DEBUG] Env HTTPS_PROXY: {os.environ.get('HTTPS_PROXY')}")
    
    try:
        resp = original_request(self, method, url, *args, **kwargs)
        print(f"[DEBUG] Response: {resp.status_code}")
        return resp
    except Exception as e:
        print(f"[DEBUG] Exception: {e}")
        raise e

requests.Session.request = patched_request

def test_akshare_debug():
    # Set proxy env vars
    proxy_url = "http://192.168.151.18:3128"
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    
    print(f"\n{'='*20} Testing Akshare with Debug Patch {'='*20}")
    
    try:
        print("Calling ak.stock_zh_a_spot_em()...")
        df = ak.stock_zh_a_spot_em()
        print(f"✅ OK ({len(df)} rows)")
    except Exception as e:
        print(f"❌ Failed: {str(e)[:100]}...")

if __name__ == "__main__":
    test_akshare_debug()
