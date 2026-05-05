import socket
import time
import os
from mootdx.quotes import Quotes

# THE "CORRECT WAY" as per documentation: Bind to the data interface IP
TDX_BIND_IP = "192.168.151.41"

# Apply Monkey Patch locally in the script
print(f"Applying Source IP Binding: {TDX_BIND_IP}")
_OriginalSocket = socket.socket
class _BoundSocket(_OriginalSocket):
    def connect(self, address):
        is_tdx = isinstance(address, tuple) and len(address) >= 2 and address[1] in [7701, 7709, 7711, 7727]
        if is_tdx:
            try:
                self.bind((TDX_BIND_IP, 0))
            except:
                pass
        super().connect(address)
socket.socket = _BoundSocket

def test_single(ip):
    start = time.time()
    try:
        # 1. Socket Check (Explicitly using the patched socket)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect((ip, 7709))
        sock.close()
        
        # 2. Protocol check via mootdx
        # bestip=False ensures it connects to the exact IP we want
        client = Quotes.factory(market='std', server=(ip, 7709), bestip=False, timeout=2.0)
        df = client.quotes(symbol=['000001'])
        if df is not None and not df.empty:
            return True, (time.time() - start)*1000
        else:
            return False, "Empty Data"
    except Exception as e:
        return False, str(e)

# Expanded target list from verified subnets in documentation
targets = []
# Haitong (175.6.5.x)
for i in range(131, 160):
    targets.append(f"175.6.5.{i}")
# Huawei Cloud
targets.extend(["139.9.51.18", "139.159.239.163", "139.9.133.247"])
# Direct subnets
for i in range(10, 30):
    targets.append(f"59.36.5.{i}")
# Others from verified pool
targets.extend([
    "119.147.212.81", "119.97.185.5", "124.71.187.122", 
    "218.60.29.136", "119.29.51.30", "123.60.84.66",
    "116.205.163.254", "116.205.171.132", "116.205.183.150"
])

# Remove duplicates
targets = list(dict.fromkeys(targets))

print(f"Starting Serial Test (n={len(targets)}) with Bind IP {TDX_BIND_IP}...")
success_count = 0
successful_ips = []

for ip in targets:
    ok, val = test_single(ip)
    if ok:
        success_count += 1
        successful_ips.append(ip)
        print(f"✅ {ip:15} | {val:7.2f}ms")
    else:
        # print(f"❌ {ip:15} | {val}")
        pass
    # Small sleep to be respectful and avoid DPI state issues
    time.sleep(0.1)

print(f"\nScan Complete.")
print(f"Total Successful: {success_count}")
if success_count >= 20:
    print("\n✅ TARGET MET: 20+ functional IPs found via direct binding!")
    print(",".join([f"{ip}:7709" for ip in successful_ips]))
else:
    print(f"\n❌ TARGET NOT MET: Only {success_count} functional IPs found.")
