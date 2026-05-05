
import asyncio
import socket
import time
import os
import pandas as pd
from mootdx.quotes import Quotes

# 广泛的通达信服务器列表
EXTENDED_SERVERS = [
    "119.147.212.81:7709", "124.71.187.122:7709", "175.6.5.153:7709", "139.9.51.18:7709",
    "139.159.239.163:7709", "47.107.64.168:7709", "119.29.19.242:7709", "123.60.84.66:7709",
    "59.36.5.11:7709", "115.238.90.165:7709", "124.160.88.183:7709", "60.191.117.167:7709",
    "180.153.18.170:7709", "180.153.18.171:7709", "180.153.18.172:7709", "218.16.123.46:7709",
    "218.75.126.9:7709", "218.108.47.69:7709", "218.108.98.244:7709", "14.215.128.18:7709",
    "59.175.238.38:7709", "113.105.142.136:7709", "121.14.110.210:7709", "121.14.2.7:7709",
    "221.231.141.60:7709", "101.227.73.20:7709", "101.227.77.20:7709", "114.80.149.32:7709",
    "114.80.149.84:7709", "124.70.190.222:7709", "139.159.239.163:7709", "124.70.1.180:7709",
    "119.3.179.6:7709", "47.100.197.6:7709", "106.15.115.176:7709", "121.14.2.14:7709"
]

async def test_tdx_protocol(ip, port, bind_ip=None):
    """
    测试 TDX 协议可用性
    """
    loop = asyncio.get_event_loop()
    start = time.time()
    
    # 模拟 socket 绑定以匹配生产环境
    # 注意：Quotes 内部创建 socket，无法直接通过参数传递 bind_ip
    # 这里我们只是测试“当前环境是否能通”
    
    try:
        # 首先尝试 raw socket connect 以快速过滤
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        if bind_ip:
            try: sock.bind((bind_ip, 0))
            except: pass
        sock.connect((ip, int(port)))
        sock.close()
        
        # 协议测试
        client = await loop.run_in_executor(
            None,
            lambda: Quotes.factory(market='std', server=(ip, int(port)), bestip=False, timeout=2)
        )
        
        # 尝试获取一个数据片段以验证协议握手完成
        data = await loop.run_in_executor(None, lambda: client.stocks(market=0))
        
        latency = (time.time() - start) * 1000
        if data is not None and not data.empty:
            return True, latency, f"OK ({len(data)} stocks)"
        return True, latency, "OK (Empty results)"
        
    except Exception as e:
        return False, 0, str(e)

async def run():
    bind_ip = os.getenv("TDX_BIND_IP", "192.168.151.111")
    env_hosts = os.getenv("TDX_HOSTS", "")
    current_hosts = [h for h in env_hosts.split(",") if h]
    
    print(f"🔍 TDX Connectivity Diagnostic (Bind: {bind_ip})")
    
    all_targets = list(set(current_hosts + EXTENDED_SERVERS))
    print(f"Testing {len(all_targets)} potential servers...\n")
    
    results = []
    # 我们并发测试以节省时间
    chunk_size = 5
    for i in range(0, len(all_targets), chunk_size):
        chunk = all_targets[i:i+chunk_size]
        tasks = []
        for s in chunk:
            ip, port = s.split(":")
            tasks.append(test_tdx_protocol(ip, port, bind_ip))
        
        chunk_results = await asyncio.gather(*tasks)
        for host, (ok, lat, msg) in zip(chunk, chunk_results):
            if ok:
                results.append((host, lat, msg))
                print(f"  ✅ {host:22} | {lat:7.2f}ms | {msg}")
            else:
                # print(f"  ❌ {host:22} | FAILED | {msg}")
                pass
    
    results.sort(key=lambda x: x[1])
    
    print("\n" + "="*80)
    print(f"{'RANK':4} | {'HOST':25} | {'LATENCY':10} | {'SOURCE'}")
    print("-" * 80)
    
    final_hosts = []
    for idx, (host, lat, msg) in enumerate(results):
        source = "CURRENT" if host in current_hosts else "NEW"
        print(f"#{idx+1:02}  | {host:25} | {lat:7.2f}ms | {source}")
        if idx < 10:
            final_hosts.append(host)
            
    print("="*80)
    print("\n🚀 Recommended TDX_HOSTS (Top 10):")
    print(",".join(final_hosts))
    
    print("\n💡 Suggestion: Update your docker-compose.node-111.yml with the above list.")

if __name__ == "__main__":
    asyncio.run(run())
