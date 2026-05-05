# 03. akshare 与 Docker 使用指南

为确保 akshare 等金融数据工具的稳定性，推荐使用**显式代理**模式，绕过透明代理的潜在干扰。

---

## 1. Python 环境使用 akshare

### 方法 A: 使用 Wrapper 脚本 (推荐)
在服务器上使用 `~/run_akshare.sh` 运行你的脚本：

```bash
~/run_akshare.sh python3 your_script.py
```

### 方法 B: 代码中设置 (云端远程 API)
如果你是调用腾讯云 (124.221.80.250) 的接口：

```python
import os
# 使用验证正确的云代理
os.environ["PROXY_URL"] = "http://192.168.151.18:3128"
os.environ["AKSHARE_API_URL"] = "http://124.221.80.250:8003"

import requests
# 显式使用代理调用
resp = requests.get(
    os.getenv("AKSHARE_API_URL") + "/api/v1/health", 
    proxies={"http": os.getenv("PROXY_URL")}
)
```

---

## 2. Docker 环境使用 akshare

推荐使用 **Host 网络模式**，性能最好且配置最简单。

### Docker Run 方式

```bash
docker run -it --rm \
  --network host \
  -e http_proxy="http://127.0.0.1:8118" \
  -e https_proxy="http://127.0.0.1:8118" \
  your-image-name \
  python your_script.py
```

### Docker Compose 方式 (推荐)

```yaml
version: '3'
services:
  get-stockdata:
    image: get-stockdata:latest
    network_mode: "host"  # 关键配置：使用主机网络
    environment:
      - TZ=Asia/Shanghai
      - PROXY_URL=http://192.168.151.18:3128       # 核心：云端专用代理
      - AKSHARE_API_URL=http://124.221.80.250:8003  # 云端端口更新
      - STOCK_DICT_API_URL=http://124.221.80.250:8000
      - ENABLE_PROXY_CHAINS=false                 # 关闭代理链，由 aiohttp 原生处理代理
```

**注意**: 如果无法使用 host 模式，请参考 `test_docker_proxy.sh` 中的方案，使用宿主机 IP (`172.17.0.1`) 和 GOST 端口 (`12345`)。
