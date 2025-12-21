# 01. 服务器端配置详情

**服务器 IP**: `192.168.151.41` (Ubuntu)

---

## 1. GOST 服务配置

我们部署了两个 GOST 实例来处理不同方向的流量。

### 1.1 gost-foreign (国外流量)
*   **端口**: `12345`
*   **用途**: 接收国外流量，转发给 SSH 隧道。支持双端口故障转移。
*   **配置文件**: `/etc/gost.json`
    ```json
    {
        "Debug": true,
        "Retries": 3,
        "ServeNodes": ["redirect://:12345"],
        "ChainNodes": [
            "http://127.0.0.1:8118"   // VS Code 隧道
        ]
    }
    ```

### 1.2 gost-domestic (国内流量)
*   **端口**: `12346`
*   **用途**: 接收国内流量，转发给内网 Squid 代理。
*   **配置文件**: `/etc/gost-domestic.json`
    ```json
    {
        "Retries": 3,
        "ServeNodes": ["redirect://:12346"],
        "ChainNodes": ["http://192.168.151.18:3128"]
    }
    ```

---

## 2. iptables 分流规则

使用 `iptables` 的 `REDIRECT` 目标将流量重定向到 GOST 端口。

**规则逻辑**:
1.  **例外规则** (优先级最高): 东方财富等特殊 IP 段 -> `12345` (走国外通道)。
    *   `175.12.0.0/16`
    *   `113.240.0.0/16`
2.  **国内规则**: 常见国内 IP 段 (43个 /8 段) -> `12346` (走 Squid)。
    *   `1.0.0.0/8`, `14.0.0.0/8`, ...
3.  **默认规则**: 其他所有流量 -> `12345` (走国外通道)。
4.  **本地回环**: `127.0.0.0/8` -> `RETURN` (不代理)。

**查看规则命令**:
```bash
sudo iptables -t nat -L GOST -n -v --line-numbers
```

---

## 3. 维护脚本

所有相关脚本位于 `e:\setup\antigravity\` (本地) 或 `~/` (远程)。

*   `deploy_optimization.sh`: 一键部署所有配置。
*   `rollback_iptables.sh`: 回滚 iptables 规则到初始状态。
