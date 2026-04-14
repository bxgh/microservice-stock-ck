import os
import tushare as ts
from dotenv import load_dotenv

load_dotenv("/app/.env.tushare")
os.environ["http_proxy"] = "http://192.168.151.18:3128"
os.environ["https_proxy"] = "http://192.168.151.18:3128"

token = os.getenv("TUSHARE_TOKEN")
ts.set_token(token)
pro = ts.pro_api()

print("Available methods in pro_api:")
methods = [m for m in dir(pro) if not m.startswith('_')]
print(methods)

# Try common ones
for m in ['shibor', 'repo_rate', 'repo_daily', 'hibor', 'libor']:
    if hasattr(pro, m):
        print(f"Testing {m}...")
        try:
            df = getattr(pro, m)(start_date='20240401', end_date='20240402')
            print(f"Success {m}: {df.columns.tolist()}")
        except Exception as e:
            print(f"Failed {m}: {e}")
