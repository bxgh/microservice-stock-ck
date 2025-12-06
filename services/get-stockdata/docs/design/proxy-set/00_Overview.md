# Antigravity 最终配置方案概览

本文档详细记录了 Antigravity 代理架构的最终配置方案。该方案实现了国内外流量智能分流、akshare 数据源的稳定访问，以及 VS Code 关闭后的自动故障转移。

---

## 1. 架构图

```mermaid
graph TD
    subgraph "远程服务器 (192.168.151.41)"
        A[应用流量 :443] -->|iptables| B{分流逻辑}
        B -->|国内IP段| C[gost-domestic :12346]
        B -->|国外IP段| D[gost-foreign :12345]
        B -->|akshare例外| D
        C --> E[Squid :3128]
        D --> F{故障转移}
        F -->|优先| G[SSH隧道 :8118 (VSCode)]
        F -->|备用| H[SSH隧道 :8119 (手动)]
    end

    subgraph "本地 Windows"
        G --> I[Privoxy :8118]
        H --> I
        I --> J[Cloudflare WARP]
        J --> K[互联网]
    end

    E --> K
```

---

## 2. 核心功能

1.  **智能分流**：
    *   **国内流量**：通过 `gost-domestic` 转发给内网 Squid 代理，直连国内网络，速度快。
    *   **国外流量**：通过 `gost-foreign` 转发给 SSH 隧道，走本地 WARP VPN，突破网络限制。
2.  **akshare 专用通道**：
    *   针对东方财富等敏感数据源，配置了 iptables 例外规则（强制走国外通道）。
    *   提供了 Docker 和 Python 的显式代理方案，确保 100% 连通性。
3.  **高可用性**：
    *   配置了双端口 (`8118`/`8119`) 故障转移。
    *   即使关闭 VS Code，只需运行本地脚本即可保持服务器代理可用。

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
**Docker**:
```bash
docker run --network host -e http_proxy="http://127.0.0.1:8118" ...
```

---

## 4. 文档索引

*   [01_Server_Configuration.md](./01_Server_Configuration.md) - 服务器端配置细节 (GOST, iptables)
*   [02_Local_Configuration.md](./02_Local_Configuration.md) - 本地 Windows 配置 (Privoxy, SSH脚本)
*   [03_Akshare_Docker_Guide.md](./03_Akshare_Docker_Guide.md) - akshare 与 Docker 使用指南
*   [04_Troubleshooting.md](./04_Troubleshooting.md) - 故障排查与维护
