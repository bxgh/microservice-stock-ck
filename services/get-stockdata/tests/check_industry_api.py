
import requests
import json
import sys

# Port 8083 per docker-compose.dev.yml (External port) 
# OR 8003 per migration guide (User Pref)
# Let's try 8003 first as that's what we set in docker-compose
BASE_URL = "http://localhost:8003/api/v1"

def check_industry_api():
    industry = "C15酒、饮料和精制茶制造业" # Baostock name
    url = f"{BASE_URL}/finance/industry/{industry}/stats"
    print(f"Requesting: {url}")
    
    try:
        # Use simple requests, assuming host networking or port forwarding
        # Note: If running inside container, localhost:8083 works (as APP runs on 8083 inside)
        # If running from host, localhost:8003 works.
        # This script is meant to be run inside container for convenience? 
        # Inside container: localhost:8083
        
        # Determine execution context
        # If running in container via "run --rm", it's a separate container joining "host" network (if network_mode: host)
        # OR "microservice-stock" network. 
        # Our docker-compose uses "network_mode: host" for dev.
        # So "localhost:8083" should work if app is running.
        
        resp = requests.get(f"http://127.0.0.1:8083/api/v1/finance/industry/{industry}/stats")
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            print("Response:")
            print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
            print("✅ API Test Passed")
        else:
            print(f"❌ API Error: {resp.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    check_industry_api()
