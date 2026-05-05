# 02. 本地 Windows 配置详情

**本地环境**: Windows + VS Code + Cloudflare WARP

---

## 1. Privoxy 配置

Privoxy 作为 HTTP 代理，负责将 SSH 隧道的流量转发给 WARP。

*   **监听端口**: `8118`
*   **配置文件**: `config.txt` (Privoxy 安装目录)
*   **关键配置**:
    ```
    listen-address  127.0.0.1:8118
    forward-socks5 / 127.0.0.1:40000 .  # 转发给 WARP
    ```

---

## 2. SSH 隧道配置

### 2.1 VS Code 自动隧道
*   **端口**: `8118`
*   **配置**: `~/.ssh/config`
    ```ssh
    Host 192.168.151.41
      RemoteForward 8118 127.0.0.1:8118
    ```
*   **行为**: VS Code 连接时自动建立，关闭时断开。
