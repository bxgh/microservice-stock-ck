# 03. akshare 与 Docker 使用指南

为确保 akshare 等金融数据工具的稳定性，推荐使用**显式代理**模式，绕过透明代理的潜在干扰。

---

## 1. Python 环境使用 akshare

### 方法 A: 使用 Wrapper 脚本 (推荐)
在服务器上使用 `~/run_akshare.sh` 运行你的脚本：

```bash
~/run_akshare.sh python3 your_script.py
```

### 方法 B: 代码中设置
在 Python 代码开头添加：

```python
import os
# 强制走 SSH 隧道代理
os.environ["http_proxy"] = "http://127.0.0.1:8118"
os.environ["https_proxy"] = "http://127.0.0.1:8118"

import akshare as ak
# ...
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

### Docker Compose 方式

```yaml
version: '3'
services:
  worker:
    image: your-image
    network_mode: "host"  # 关键配置
    environment:
      - http_proxy=http://127.0.0.1:8118
      - https_proxy=http://127.0.0.1:8118
    command: python your_script.py
```

**注意**: 如果无法使用 host 模式，请参考 `test_docker_proxy.sh` 中的方案，使用宿主机 IP (`172.17.0.1`) 和 GOST 端口 (`12345`)。
