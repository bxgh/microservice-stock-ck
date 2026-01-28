import os
import requests

api_key = os.getenv("SILICONFLOW_API_KEY")
if not api_key:
    print("No API Key")
    exit(1)

url = "https://api.siliconflow.cn/v1/models"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        models = response.json().get("data", [])
        print("Available Models:")
        for m in models:
            print(f"- {m['id']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Exception: {e}")
