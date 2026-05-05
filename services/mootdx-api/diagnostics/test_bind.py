
import socket
import time
from mootdx.quotes import Quotes
import os

def test_config(bind_ip=None):
    ip = "119.147.212.81"
    port = 7709
    print(f"\n--- Testing IP: {ip}:{port} (Bind: {bind_ip}) ---")
    
    start = time.time()
    try:
        # Socket test
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        if bind_ip:
            sock.bind((bind_ip, 0))
        sock.connect((ip, port))
        print(f"  Socket connected in {(time.time()-start)*1000:.2f}ms")
        sock.close()
        
        # Mootdx test
        try:
            # We can't easily tell Quotes to bind, but we can see if it works naturally
            client = Quotes.factory(market='std', server=(ip, port), bestip=False, timeout=5)
            # If we are here, connect() worked (it calls setup() internally)
            print("  Mootdx connected and setup successful!")
            return True
        except Exception as e:
            print(f"  Mootdx Fail: {str(e)}")
            return False
    except Exception as e:
        print(f"  Socket Fail: {str(e)}")
        return False

if __name__ == "__main__":
    # Test with standard bind (111)
    test_config("192.168.151.111")
    # Test without bind (default interface)
    test_config(None)
    # Test with another interface if possible (37 is ens35)
    test_config("192.168.151.37")
