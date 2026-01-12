# Server 111 网络配置详解 (3-NIC Architecture)

> **更新日期**: 2026-01-12
> **服务器**: Server 111 (Worker / Tick Acquisition Node)
> **环境**: 生产环境 (Production)

本文档详细描述了 Server 111 的 **三网卡物理隔离架构**，该架构旨在实现管理流量、数据同步流量与外部代理流量的物理隔离，以最大化网络吞吐稳定性和安全性。

---

## 🏗️ 物理网卡配置 (Physical Interfaces)

Server 111 配备了三块千兆虚拟网卡 (VMXNET3)，分别对应不同的业务平面。

| 接口名称 | IP 地址 (CIDR) | 网关 | 跃点数 (Metric) | 角色 | 描述 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ens35** | `192.168.151.37` | `.254` | 100 (Default) | **管理 / 出口** | SSH 管理、默认公网出口、Git 拉取 |
| **ens34** | `192.168.151.36` | `.254` | 200 | **代理 / 爬虫** | 专用于 HTTP/HTTPS 代理流量 (Proxy) |
| **ens32** | `192.168.151.111` | `.254` | 300 | **集群 / 数据** | 内部 ClickHouse/Redis 同步、TDX 行情直连 |

---

## 🛣️ 路由策略 (Routing Policies)

为了确保流量走正确的物理路径，系统通过静态路由表进行了严格划分。

### 1. 默认路由 (Default Routes)
系统存在三条默认路由，但优先级不同 (Metric 越小优先级越高)：
1.  **Metric 100 (`ens35`)**: 所有未匹配的流量（如 `apt update`, `git pull`）默认从 `192.168.151.37` 发出。
2.  Metric 200 (`ens34`): 备用。
3.  Metric 300 (`ens32`): 备用。

### 2. 静态集群路由 (Cluster Static Routes)
为了保证分布式数据库 (ClickHouse/Redis) 的数据同步不占用管理带宽，且拥有最低的内部延迟，**强制**与其他节点及其代理服务器的通信走专用网卡。

```bash
# 目标：Server 41 (Orchestrator/Shard 0)
192.168.151.41 via 192.168.151.111 dev ens32  # 走数据网卡 (ens32)

# 目标：Server 58 (Shard 1)
192.168.151.58 via 192.168.151.111 dev ens32  # 走数据网卡 (ens32)

# 目标：Proxy Server (代理服务器)
192.168.151.18 via 192.168.151.36  dev ens34  # 走代理网卡 (ens34)
```

**策略解读**：
*   **数据平面隔离**：Server 111 <-> 41/58 之间的大流量同步（ClickHouse Replica, Redis Cluster Gossip）全部被锁定在 `ens32` 上。
*   **代理平面隔离**：爬虫请求（如请求 `192.168.151.18:3128`）被强制锁定在 `ens34` 上，防止爬虫流量打满数据网卡。

---

## 🐳 Docker 网络集成

Docker 容器（如 `mootdx-api`）使用 `network_mode: host`，因此直接继承宿主机的网络特征。

### `mootdx-api` 的特殊配置
由于 TDX 行情接口需要极高的稳定性，且 Server 111 的上层防火墙对不同源 IP 有严格的 DPI 策略，我们采用了 **源 IP 绑定 (Source IP Binding)** 技术。

*   **配置项**: `TDX_BIND_IP=192.168.151.111`
*   **效果**:
    *   `mootdx-api` 强制使用 `192.168.151.111` 作为 Socket 发起端的源 IP。
    *   内核根据路由规则，将源为 `.111` 的流量匹配到 `ens32` 网卡。
    *   **结果**: TDX 行情流量实际上是作为“内部高优先级数据”通过 `ens32` 发出的。这绕过了可能对 `.37` (管理 IP) 施加的更严格的 QoS 或防火墙限制。

---

## 📊 流量拓扑图

```mermaid
graph TD
    subgraph "Server 111 (Linux Kernel Routing)"
        Default_Traffic[默认流量<br/>(SSH, Git, Apt)]
        Proxy_Traffic[爬虫代理流量<br/>(To 192.168.151.18)]
        Cluster_Traffic[集群数据流量<br/>(ClickHouse, Redis)]
        TDX_Traffic[TDX 行情流量<br/>(Bind .111)]

        NIC1[[ens35 / .37<br/>管理网卡]]
        NIC2[[ens34 / .36<br/>代理网卡]]
        NIC3[[ens32 / .111<br/>数据网卡]]

        Default_Traffic -->|Metric 100| NIC1
        Proxy_Traffic -->|Static Route| NIC2
        Cluster_Traffic -->|Static Route| NIC3
        TDX_Traffic -->|Bind IP + Policy| NIC3
    end

    Switch((核心交换机))

    NIC1 --> Switch
    NIC2 --> Switch
    NIC3 --> Switch

    Switch -->|VLAN Default| Internet_Gateway[公网出口]
    Switch -->|VLAN Cluster| Server41_58[Server 41 & 58]
    Switch -->|VLAN Proxy| ProxyServer[Proxy .18]
```

## ✅ 验证命令

如果您需要验证上述配置，请运行以下指令：

1.  **查看 IP 与物理网卡对应关系**:
    ```bash
    ip addr show
    ```
2.  **查看路由表 (确认 Cluster 流量走 ens32)**:
    ```bash
    ip route list | grep ens32
    ```
3.  **测试路由决策**:
    ```bash
    ip route get 192.168.151.41  # 应显示 dev ens32
    ip route get 192.168.151.18  # 应显示 dev ens34
    ip route get 8.8.8.8         # 应显示 dev ens35
    ```
