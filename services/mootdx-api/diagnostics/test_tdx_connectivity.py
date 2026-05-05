
import socket
import time
import asyncio
from mootdx.quotes import Quotes
import os

# 扩展的潜在 TDX 服务器列表
POTENTIAL_SERVERS = [
    "119.147.212.81:7709",
    "124.71.187.122:7709",
    "175.6.5.153:7709",
    "139.9.51.18:7709",
    "139.159.239.163:7709",
    "47.107.64.168:7709",
    "119.29.19.242:7709",
    "123.60.84.66:7709",
    "59.36.5.11:7709",
    "115.238.90.165:7709",
    "124.160.88.183:7709",
    "60.191.117.167:7709",
    "180.153.18.170:7709",
    "180.153.18.171:7709",
    "180.153.18.172:7709",
    "218.16.123.46:7709",
    "218.75.126.9:7709",
    "218.108.47.69:7709",
    "218.108.98.244:7709",
    "14.215.128.18:7709",
    "59.175.238.38:7709",
    "113.105.142.136:7709",
    "121.14.110.210:7709",
    "121.14.2.7:7709",
    "221.231.141.60:7709",
]

async def test_server(ip, port):
    start = time.time()
    try:
        # 1. Socket 连接测试
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        bind_ip = os.getenv("TDX_BIND_IP")
        if bind_ip:
            try:
                sock.bind((bind_ip, 0))
            except:
                pass
        
        sock.connect((ip, int(port)))
        latency = (time.time() - start) * 1000
        sock.close()
        
        # 2. Mootdx 协议测试
        try:
            # 使用同步 factory 在线程池中执行
            loop = asyncio.get_event_loop()
            client = await loop.run_in_executor(
                None, 
                lambda: Quotes.factory(market='std', server=(ip, int(port)), bestip=False, timeout=2)
            )
            # 获取个股数量作为可用性检查 (SH 分装号 1)
            count = await loop.run_in_executor(None, lambda: client.get_security_count(0))
            if count > 0:
                return True, latency, f"OK (Count: {count})"
            else:
                return True, latency, "OK (Empty market?)"
        except Exception as e:
            return True, latency, f"Socket OK, Mootdx Protocol Fail: {str(e)}"
            
    except Exception as e:
        return False, 0, f"Failed: {str(e)}"

async def run_diagnostic():
    env_hosts = os.getenv("TDX_HOSTS", "")
    current_hosts = env_hosts.split(",") if env_hosts else []
    
    print(f"Testing environment: BIND_IP={os.getenv('TDX_BIND_IP')}")
    
    # 合并并去重
    all_to_test = list(set(current_hosts + POTENTIAL_SERVERS))
    
    print(f"Starting test for {len(all_to_test)} servers...\n")
    
    tasks = []
    for s in all_to_test:
        if ":" in s:
            ip, port = s.split(":")
            tasks.append(test_server(ip, port))
            
    results = await asyncio.gather(*tasks)
    
    successful = []
    for i, (ok, latency, msg) in enumerate(results):
        host = all_to_test[i]
        if ok:
            successful.append((host, latency, msg))
            
    # 按延迟排序
    successful.sort(key=lambda x: x[1])
    
    print(f"{'HOST':25} | {'LATENCY':10} | {'STATUS/MESSAGE'}")
    print("-" * 60)
    for host, latency, msg in successful:
        status = "✅" if "OK" in msg else "⚠️"
        print(f"{status} {host:22} | {latency:7.2f}ms | {msg}")

    print("\n--- Top 8 Fastest and Working IPs for TDX_HOSTS ---")
    fast_and_ok = [x[0] for x in successful if "OK" in x[2]][:8]
    print(f"TDX_HOSTS={','.join(fast_and_ok)}")

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
