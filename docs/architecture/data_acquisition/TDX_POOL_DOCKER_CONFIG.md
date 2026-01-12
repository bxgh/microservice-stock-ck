# Mootdx API 容器部署与 TDX连接池配置指南

> **适用范围**: Server 111 (Tick 采集节点)
> **服务**: `mootdx-api` (Docker 容器)
> **目的**: 确保容器能正确穿透防火墙策略，连接到高可用的 TDX 行情源。

在 Server 111 特殊的三网卡与防火墙环境下，部署 `mootdx-api` 必须严格遵循以下配置规范，否则将导致连接超时或被重置 (Connection Reset)。

---

## 1. 核心网络概览

由于上层防火墙对 7709 端口实施了深度包检测 (DPI)，且仅放行来自特定物理出口 (`ens32`) 的流量，容器 **不能采用默认的 Bridge 模式**。

**必须满足的三大条件**:
1.  **Network Mode**: 必须为 `host`，以继承宿主机的路由表。
2.  **Bind IP**: 必须显式绑定 `192.168.151.111`，触发内核策略路由 (Policy Routing)。
3.  **Use Verified Hosts**: 必须仅连接已验证的白名单节点。

---

## 2. Docker Compose 配置规范

以下是标准化的 `docker-compose` 配置模板：

```yaml
version: '3.8'

services:
  mootdx-api:
    image: microservice-stock-mootdx-api:latest
    container_name: microservice-stock-mootdx-api
    
    # [关键配置 1] 网络模式必须为 host
    # 原因：Bridge 模式下的 NAT 会导致源 IP 变为 Docker0 网桥 IP
    # 从而导致宿主机无法正确匹配 "from 192.168.151.111" 的路由规则，
    # 流量可能会错误地从默认网关 (ens35) 溜出，被防火墙拦截。
    network_mode: host
    
    restart: unless-stopped
    environment:
      # [关键配置 2] 强制绑定源 IP
      # 作用：Python socket 在 connect() 前会执行 bind(('192.168.151.111', 0))
      # 结果：内核看到源 IP 为 .111，强制将包路由至 ens32 网卡。
      - TDX_BIND_IP=192.168.151.111
      
      # [关键配置 3] 使用白名单 IP 池
      # 作用：仅连接华为云和海通证券等已验证通畅的 DPI 白名单节点。
      # 注意：不要开启 TDX_AUTO_DISCOVER，自动发现的 IP 99% 会被墙。
      - TDX_AUTO_DISCOVER=false
      - TDX_HOSTS=175.6.5.153:7709,175.6.5.154:7709,175.6.5.155:7709,175.6.5.156:7709,139.9.133.247:7709,139.9.51.18:7709,139.159.239.163:7709
      
      # [推荐配置] 连接池大小
      # 建议设置为可用节点数的一半左右，保留冗余。
      - TDX_POOL_SIZE=5
      
      # 基础服务配置
      - PORT=8003
      - HOST=0.0.0.0
      - LOG_LEVEL=INFO

    # 挂载卷 (可选，用于日志和调试)
    volumes:
      - ./logs/mootdx-api:/app/logs
```

---

## 3. 为什么必须这样配置？ (原理分析)

### 关于 `network_mode: host`
*   **Bridge 模式 (默认)**: 容器发出的包，源 IP 是 `172.17.0.x`。经过 Docker NAT (Masquerade) 后，宿主机看其源 IP 通常是主网卡 IP (`192.168.151.37`, ens35)。
*   **后果**: `ens35` 是管理网口，流量出去会被上层防火墙识别为“来自非信任区域的 7709 请求”，直接丢弃。
*   **Host 模式**: 容器与宿主机共享网络栈。当应用绑定 `192.168.151.111` 时，发出的包源 IP 就是 `192.168.151.111`。

### 关于 `TDX_BIND_IP`
*   **不绑定时**: 即使在 Host 模式下，系统通常会根据目标 IP 查路由表选择源 IP。虽然我们配置了静态路由，但显式绑定是双重保险。
*   **绑定后**: `bind()` 调用强制指定了 Socket 的源地址。Linux 内核的策略路由规则 (Policy Routing Rule) 会检测到 `from 192.168.151.111`，并强制查找特定路由表，最终从 `ens32` 物理网卡发送。

---

## 4. 验证部署是否成功

部署后，请执行以下步骤验证：

1.  **检查容器日志**:
    确认连接池初始化时节点状态为 `connected`。
    ```bash
    docker logs -f microservice-stock-mootdx-api
    # 应看到: Node x/5 connected
    ```

2.  **运行诊断脚本**:
    使用内置的复核工具确保应用应用了正确的 IP。
    ```bash
    docker exec microservice-stock-mootdx-api python /app/diagnostics/verify_tdx_20260112.py
    ```
