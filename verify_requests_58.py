import httpx
import json

def fetch(start):
    url = "http://127.0.0.1:8003/api/v1/tick/000001"
    params = {"date": 20251202, "start": start, "offset": 2000}
    try:
        print(f"Requesting start={start}...", flush=True)
        resp = httpx.get(url, params=params, timeout=5)
        print(f"Status: {resp.status_code}", flush=True)
        if resp.status_code == 200:
            data = resp.json()
            print(f"Data len: {len(data)}", flush=True)
            if data:
                print(f"First: {data[0].get('time')}", flush=True)
        else:
            print(f"Error status: {resp.text}", flush=True)
    except Exception as e:
        print(f"Exception: {e}", flush=True)

if __name__ == "__main__":
    fetch(0)
    fetch(2000)
