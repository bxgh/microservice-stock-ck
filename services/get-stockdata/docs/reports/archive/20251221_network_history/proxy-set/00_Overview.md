# Antigravity 最终配置方案概览

本文档详细记录了 Antigravity 代理架构的最终配置方案。该方案实现了国内外流量智能分流、akshare 数据源的稳定访问，以及 VS Code 关闭后的自动故障转移。

---

## 1. 架构图

```mermaid
graph TD
    subgraph "远程服务器 (192.168.151.41)"
        A[应用流量] -->|iptables| B{分流逻辑}
        B -->|国内/云端| C[Squid :3128]
        B -->|国外/AkShare| D[gost-foreign :12345]
        C -->|云端端点| H1[Cloud Dict :8000]
        C -->|云端端点| H2[AkShare API :8003]
        D --> G[SSH隧道 :8118 (VSCode)]
    end

    subgraph "本地 Windows"
        G --> I[Privoxy :8118]
        H --> I
        I --> J[Cloudflare WARP]
        J --> K[互联网]
    end

    C --> K
```

---

## 2. 核心功能

1.  **智能分流**：
    *   **国内流量**：通过 `gost-domestic` 转发给内网 Squid 代理，直连国内网络，速度快。
    *   **国外流量**：通过 `gost-foreign` 转发给 SSH 隧道，走本地 WARP VPN，突破网络限制。
2.  **云端数据源专用通道**：
    *   针对云端 API (`124.221.80.250`) 的所有请求，强制使用内网 Squid 代理 (`192.168.151.18:3128`)。
    *   Docker 容器采用 **Host 网络模式**，允许程序显式配置代理绕过透明分流，确保 100% 连通性。
    *   云端端口分配：股票字典 (8000), AkShare (8003), Baostock (8001), Pywencai (8002)。3.  **高可用性**：
    *   即使关闭 VS Code，可以通过建立本地 SSH 隧道保持服务器代理可用。

---

## 3. 快速开始

### 3.1 日常开发 (VS Code)
直接连接 VS Code Remote-SSH，无需额外操作。流量自动分流。

### 3.2 离线任务 (VS Code 关闭)
运行本地脚本 `e:\setup\antigravity\keep_ssh_tunnel.ps1`，保持代理在线。

### 3.3 运行 akshare
**Python**:
```bash
~/run_akshare.sh python your_script.py
```
**Docker (Host模式)**:
```bash
docker run --network host \
  -e PROXY_URL="http://192.168.151.18:3128" \
  -e AKSHARE_API_URL="http://124.221.80.250:8003" \
  your-image
```

---

## 4. 文档索引

*   [01_Server_Configuration.md](./01_Server_Configuration.md) - 服务器端配置细节 (GOST, iptables)
*   [02_Local_Configuration.md](./02_Local_Configuration.md) - 本地 Windows 配置 (Privoxy, SSH脚本)
*   [03_Akshare_Docker_Guide.md](./03_Akshare_Docker_Guide.md) - akshare 与 Docker 使用指南
*   [04_Troubleshooting.md](./04_Troubleshooting.md) - 故障排查与维护
