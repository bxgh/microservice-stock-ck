import socket
import os
import concurrent.futures
from mootdx.quotes import Quotes

TDX_BIND_IP = "192.168.151.41"

# Standard MonkeyPatch
_OriginalSocket = socket.socket
class _BoundSocket(_OriginalSocket):
    def connect(self, address):
        if isinstance(address, tuple) and address[1] in [7709]:
            try:
                self.bind((TDX_BIND_IP, 0))
            except:
                pass
        super().connect(address)
socket.socket = _BoundSocket

def check_ip(ip):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect((ip, 7709))
        s.close()
        
        # Real Protocol check
        client = Quotes.factory(market='std', server=(ip, 7709), bestip=False, timeout=1.0)
        df = client.quotes(symbol=['000001'])
        if df is not None and not df.empty:
            return ip
    except:
        pass
    return None

def main():
    # Expand search significantly
    all_targets = set()
    
    # 1. Standard subnets from known TDX servers
    prefixes = [
        "59.36.5.", "59.36.102.", "119.147.212.", "113.105.142.",
        "121.14.110.", "121.14.104.", "58.251.114.", "114.80.149.",
        "221.231.141.", "218.60.29.", "119.97.185."
    ]
    
    for pref in prefixes:
        for i in range(1, 255): # Full C-segment scan
            all_targets.add(f"{pref}{i}")
            
    print(f"Global Direct Scan (n={len(all_targets)}) via Bind {TDX_BIND_IP}...")
    
    found = []
    # Use high workers as most will fail fast
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        for ip in executor.map(check_ip, list(all_targets)):
            if ip:
                found.append(ip)
                print(f"✅ FOUND: {ip}")
                if len(found) >= 20:
                    print("!!! REACHED 20 !!!")
                    # break # We could break but let's see how many we get
    
    print(f"\nFinal Count: {len(found)}")
    if found:
        print("Successful IPs: " + ",".join(found))

if __name__ == "__main__":
    main()
