
import socket
import time

def test_connect(target_ip, target_port, bind_ip):
    print(f"Testing connection to {target_ip}:{target_port} binding to {bind_ip}...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2) # Faster timeout
    try:
        s.bind((bind_ip, 0))
        start = time.time()
        s.connect((target_ip, target_port))
        latency = (time.time() - start) * 1000
        print(f"✅ Success! Latency: {latency:.2f}ms")
        s.close()
        return True
    except Exception as e:
        # print(f"❌ Failed: {e}") # Reduce noise
        return False

if __name__ == "__main__":
    # Comprehensive Hardcoded List (SH + SZ)
    targets = [
        # SH (Standard)
        ("119.147.212.81", 7709), ("119.97.185.5", 7709), ("124.71.187.122", 7709), ("218.60.29.136", 7709),
        ("59.36.5.11", 7709), ("175.6.5.153", 7709), ("119.29.51.30", 7709), ("175.6.5.154", 7709),
        ("175.6.5.155", 7709), ("175.6.5.156", 7709), ("139.9.133.247", 7709), ("139.9.51.18", 7709),
        ("139.159.239.163", 7709), ("121.14.2.7", 7709), ("119.147.164.60", 7709), ("119.147.171.206", 7709),
        ("113.105.142.136", 7709), ("114.80.63.12", 7709), ("114.80.63.35", 7709), ("180.153.18.170", 7709),
        # SZ (Standard)
        ("123.125.108.23", 7709), ("123.125.108.24", 7709), ("119.147.212.81", 7709), ("113.105.142.133", 7709),
        ("115.238.56.198", 7709), ("218.75.126.9", 7709), ("111.160.159.63", 7709), ("61.135.142.73", 7709),
        ("114.80.63.12", 7709), ("114.80.63.35", 7709), ("113.9.11.196", 7709), ("14.17.75.71", 7709),
        ("42.4.114.93", 7709), ("221.231.141.60", 7709), ("58.215.8.15", 7709), ("101.69.172.16", 7709)
    ]
    targets = list(set(targets))
    
    bind_ip = "192.168.151.41"
    
    print(f"\n--- Testing usage of Source IP: {bind_ip} against {len(targets)} servers ---")
    success_count = 0
    valid_hosts = []
    
    for ip, port in targets:
        if test_connect(ip, port, bind_ip):
            success_count += 1
            valid_hosts.append(f"{ip}:{port}")
            
    print(f"\nResult: {success_count}/{len(targets)} passed using bind_ip={bind_ip}")
    print(f"Valid Hosts: {','.join(valid_hosts)}")
