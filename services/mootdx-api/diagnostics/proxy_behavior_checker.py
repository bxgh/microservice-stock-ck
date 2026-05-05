import socket
import struct
import time

def socks5_test(target_ip, target_port, proxy_host='127.0.0.1', proxy_port=12345):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((proxy_host, proxy_port))
        
        # SOCKS5 Handshake
        s.sendall(b'\x05\x01\x00')
        if s.recv(2) != b'\x05\x00': return False
        
        # Connect to destination
        ip_bytes = socket.inet_aton(target_ip)
        port_bytes = struct.pack('!H', target_port)
        s.sendall(b'\x05\x01\x00\x01' + ip_bytes + port_bytes)
        
        reply = s.recv(10)
        if reply and reply[1] == 0:
            # Send a basic TDX ping/handshake if we could, but socket success is a good start
            s.close()
            return True
    except: pass
    return False

# IPs that are usually failing/resetting
targets = [
    '119.147.212.81', '218.60.29.136', '124.71.187.122', '119.97.185.5',
    '119.29.51.30', '121.14.2.7', '113.105.142.133', '222.73.13.138'
]

print("Comparing Proxies for Domestic TDX Nodes:")
for ip in targets:
    res_sg = socks5_test(ip, 7709, '127.0.0.1', 12345) # Singapore
    res_cn = socks5_test(ip, 7709, '127.0.0.1', 12346) # Domestic/Squid
    print(f"{ip:15} | SG Tunnel: {'✅' if res_sg else '❌'} | CN Squid: {'✅' if res_cn else '❌'}")
