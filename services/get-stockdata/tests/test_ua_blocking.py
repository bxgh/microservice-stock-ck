import os
import requests
import logging

# Enable verbose logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

def test_ua_blocking():
    proxy_url = "http://127.0.0.1:8118"
    proxies = {"http": proxy_url, "https": proxy_url}
    
    target_url = "https://82.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
    
    # 1. Default UA (python-requests)
    print(f"\n{'='*20} Testing Default UA {'='*20}")
    try:
        resp = requests.get(target_url, proxies=proxies, timeout=10)
        print(f"✅ Default UA: OK ({resp.status_code})")
    except Exception as e:
        print(f"❌ Default UA: Failed: {str(e)[:100]}...")

    # 2. Browser UA (from Akshare)
    print(f"\n{'='*20} Testing Browser UA {'='*20}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
    }
    try:
        resp = requests.get(target_url, headers=headers, proxies=proxies, timeout=10)
        print(f"✅ Browser UA: OK ({resp.status_code})")
    except Exception as e:
        print(f"❌ Browser UA: Failed: {str(e)[:100]}...")

if __name__ == "__main__":
    test_ua_blocking()
