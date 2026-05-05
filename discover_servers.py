
import sys
from mootdx.quotes import Quotes

def discover_best_servers(count=5):
    print("Scanning for best TDX servers...")
    try:
        # Enable bestip=True to let mootdx find the fastest servers
        client = Quotes.factory(market='std', bestip=True)
        
        
        # Determine which server was picked
        # From previous dir check: 'ip', 'port' are available on client.client
        api = client.client
        print(f"Selected Server: {api.ip}:{api.port}")
        
    except Exception as e:
        print(f"Error during discovery: {e}")

if __name__ == "__main__":
    # Run multiple times to potentially pick different servers if random
    for i in range(5):
        print(f"\n--- Attempt {i+1} ---")
        discover_best_servers()
