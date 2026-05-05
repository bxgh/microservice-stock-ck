import requests
import os

def test_requests():
    print("Testing requests with proxy...")
    print(f"http_proxy: {os.environ.get('http_proxy')}")
    print(f"https_proxy: {os.environ.get('https_proxy')}")
    
    url = "https://82.push2.eastmoney.com/"
    try:
        # Note: verify=False to avoid SSL cert issues if any, though curl worked with it
        resp = requests.get(url, timeout=10, verify=False)
        print(f"Status Code: {resp.status_code}")
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_requests()
