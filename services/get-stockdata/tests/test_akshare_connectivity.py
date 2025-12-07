import os
import akshare as ak
import requests
import logging
import time
import socket

# Enable verbose logging for requests/urllib3
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

def test_proxy(proxy_url, name):
    print(f"\n{'='*20} Testing Proxy: {name} ({proxy_url}) {'='*20}")
    
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    } if proxy_url else None
    
    # 1. EastMoney (Direct Request)
    target_url = "https://82.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
    
    try:
        print("  Testing EastMoney (Direct Request)...", end=" ", flush=True)
        resp = requests.get(target_url, proxies=proxies, timeout=10)
        print(f"✅ OK ({resp.status_code})")
    except Exception as e:
        print(f"❌ Failed: {str(e)[:100]}...")

    # 2. Akshare (Env Var Injection)
    if proxy_url:
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
    else:
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)
        
    try:
        print("  Testing Akshare (Library Call)...", end=" ", flush=True)
        # Try to fetch just one page if possible, but stock_zh_a_spot_em fetches all
        # We can try a simpler function?
        df = ak.stock_zh_a_spot_em()
        print(f"✅ OK ({len(df)} rows)")
    except Exception as e:
        print(f"❌ Failed: {str(e)[:100]}...")

def main():
    # Only test the working configuration
    test_proxy("http://127.0.0.1:8118", "Current Env")

if __name__ == "__main__":
    main()
