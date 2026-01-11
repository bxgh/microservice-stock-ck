
import time
import logging
import socket
import os
from mootdx.quotes import Quotes

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Target to test
SYMBOLS = ['000001', '600000']
DATES = ['20260109']

def get_candidates():
    # User's suggested IP pool + Known Control
    return [
        ('175.6.5.153', 7709, 'User-1'),
        ('139.9.51.18', 7709, 'User-2'),
        ('139.159.239.163', 7709, 'User-3'),
        ('119.147.212.81', 7709, 'User-4'),
        ('124.71.187.122', 7709, 'User-5'),
        ('59.36.5.11', 7709, 'Known-Good')
    ]

def get_local_ips():
    return ['192.168.151.41', '192.168.151.47', '192.168.151.49']

class BoundSocket(socket.socket):
    _local_ip = None
    def connect(self, address):
        if self._local_ip:
            try:
                self.bind((self._local_ip, 0))
            except Exception as e:
                # logger.warning(f"Failed to bind {self._local_ip}: {e}")
                pass
        super().connect(address)

def test_server(ip, port, name, bind_ip):
    # Apply monkey patch for this specific test
    original_socket = socket.socket
    socket.socket = BoundSocket
    BoundSocket._local_ip = bind_ip
    
    try:
        client = Quotes.factory(market='std', bestip=False, server=(ip, port), timeout=5)
        for symbol in SYMBOLS:
            for date in DATES:
                try:
                    data = client.transactions(symbol=symbol, date=date)
                    if data is not None and not data.empty:
                        logger.info(f"✅ [Bind:{bind_ip}] [{name}] {ip}:{port} | {symbol} -> SUCCESS")
                        return True
                except Exception:
                    continue
        logger.info(f"❌ [Bind:{bind_ip}] [{name}] {ip}:{port} -> FAILED")
        return False
    except Exception as e:
        logger.info(f"🔥 [Bind:{bind_ip}] [{name}] {ip}:{port} -> ERROR ({str(e)})")
        return False
    finally:
        socket.socket = original_socket

if __name__ == "__main__":
    local_ips = get_local_ips()
    tdx_servers = get_candidates()
    
    logger.info(f"Starting Cross-Binding Scan...")
    logger.info(f"Local IPs: {local_ips}")
    logger.info(f"TDX Servers: {[s[0] for s in tdx_servers]}")
    
    results = []
    for bind_ip in local_ips:
        logger.info(f"\n--- Testing with Source IP: {bind_ip} ---")
        for ip, port, name in tdx_servers:
            if test_server(ip, port, name, bind_ip):
                results.append(f"Local:{bind_ip} -> TDX:{ip} ({name})")
            
    logger.info("\n" + "="*50)
    logger.info("WORKING COMBINATIONS SUMMARY:")
    for res in results:
        logger.info(res)
    logger.info("="*50)
