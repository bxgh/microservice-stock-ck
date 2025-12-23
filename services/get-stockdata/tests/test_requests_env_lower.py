import os
import requests
import logging

# Enable verbose logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

def test_requests_env():
    proxy_url = "http://192.168.151.18:3128"
    
    # Clear existing
    for key in list(os.environ.keys()):
        if "proxy" in key.lower():
            os.environ.pop(key)
            
    # Set lowercase
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url
    
    target_url = "https://82.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
    
    print(f"\n{'='*20} Testing Requests with Lowercase Env Vars {'='*20}")
    print(f"http_proxy: {os.environ.get('http_proxy')}")
    print(f"https_proxy: {os.environ.get('https_proxy')}")
    
    try:
        # NO proxies argument!
        resp = requests.get(target_url, timeout=10)
        print(f"✅ OK ({resp.status_code})")
    except Exception as e:
        print(f"❌ Failed: {str(e)[:100]}...")

if __name__ == "__main__":
    test_requests_env()
