# 04. 故障排查手册

---

## 1. 无法连接 Google / 国外网站

**现象**: `curl -I https://www.google.com` 超时或报错。

**排查步骤**:
1.  **检查 SSH 隧道**:
    *   在服务器运行: `curl -I -x http://127.0.0.1:8118 https://www.google.com`
    *   如果失败: 检查本地 VS Code 是否连接，或 `keep_ssh_tunnel.ps1` 是否运行。
2.  **检查 GOST 服务**:
    *   `sudo systemctl status gost`
    *   `sudo netstat -tulpn | grep 12345`
3.  **检查本地 Privoxy**:
    *   确保本地 Windows 的 Privoxy 服务正在运行。

---

## 2. 无法连接 东方财富 / akshare 报错

**现象**: akshare 获取数据超时或 SSL 错误。

**排查步骤**:
1.  **确认代理设置**:
    *   确保使用了显式代理 (`http_proxy=http://127.0.0.1:8118`)。
2.  **测试连通性**:
    *   `curl -I -x http://127.0.0.1:8118 https://datacenter.eastmoney.com`
3.  **检查例外规则 (如果是透明代理)**:
    *   `sudo iptables -t nat -L GOST -n | grep 175.12`
    *   确认相关 IP 段已重定向到 `12345`。

---

## 3. VS Code 关闭后代理失效

**现象**: 关闭 VS Code 后服务器无法上网。

**解决**:
1.  在本地 Windows 运行 `keep_ssh_tunnel.ps1` (确保脚本配置为 RemoteForward 8118)。
2.  确保 PowerShell 窗口保持开启。
3.  GOST 会自动通过 `8118` 端口继续工作。

---

## 4. 常用维护命令

*   **重启所有服务**:
    ```bash
    sudo systemctl restart gost gost-domestic
    ```
*   **查看实时日志**:
    ```bash
    sudo journalctl -u gost -f
    ```
*   **保存 iptables 规则**:
    ```bash
    sudo netfilter-persistent save
    ```
