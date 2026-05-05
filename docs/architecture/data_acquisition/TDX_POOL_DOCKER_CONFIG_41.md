# Mootdx API 容器部署与 TDX连接池配置指南 (Server 41)

> **适用范围**: Server 41 (Orchestrator / Shard 1)
> **服务**: `mootdx-api` (Docker 容器)
> **目的**: 确保容器能正确穿透防火墙策略，连接到高可用的 TDX 行情源。

在 Server 41 的三网卡环境下，部署 `mootdx-api` 必须严格遵循以下配置规范，以确保与计算节点 (58/111) 保持一致的采集性能与安全性。

---

## 1. 核心网络概览

由于上层防火墙对 7709 端口实施了深度包检测 (DPI)，**禁止裸连 7709 端口**（仅 `59.36.5.11` 例外）。

**必须满足的核心条件**:
1.  **Network Mode**: 必须为 `host`，以触发宿主机的透明代理拦截逻辑。
2.  **iptables 协同**: 必须确保宿主机 NAT 表中没有针对 7709 端口的 `RETURN` 规则（详见 *网卡修复文档*）。
3.  **Use Optimized Hosts**: 必须优先连接华为云（139.x）、海通（175.x）等已被验证能通过代理链路穿透的节点。

---

## 2. Docker Compose 配置规范

以下是 Server 41 专用的配置模板：

```yaml
version: '3.8'

services:
  mootdx-api:
    image: microservice-stock-mootdx-api:latest
    container_name: microservice-stock-mootdx-api
    
    # [关键配置 1] 网络模式必须为 host
    # 原因：确保宿主机正确匹配 "from 192.168.151.41" 的路由规则。
    network_mode: host
    
    restart: unless-stopped
    environment:
      # [可选] 强制绑定数据网段 IP
      # 警告：如果不带透明代理链路直接强绑，部分受管网段可能会拦截流量。
      # 目前建议由宿主机 IP Stack 自动管理，或仅在集群内部流量中使用。
      - TDX_BIND_IP=192.168.151.41
      
      # [关键配置 3] 使用白名单 IP 池
      - TDX_AUTO_DISCOVER=false
      - TDX_HOSTS=175.6.5.153:7709,175.6.5.154:7709,175.6.5.155:7709,175.6.5.156:7709,139.9.133.247:7709,139.9.51.18:7709,139.159.239.163:7709
      
      # [推荐配置] 连接池大小
      - TDX_POOL_SIZE=5
      
      # 基础服务配置
      - PORT=8003
      - HOST=0.0.0.0
      - LOG_LEVEL=INFO

    volumes:
      - ./logs/mootdx-api:/app/logs
```

---

## 3. 部署验证

1.  **检查容器日志**:
    ```bash
    docker logs -f microservice-stock-mootdx-api
    ```

2.  **确认源 IP 绑定**:
    在容器内执行网络连接检查，确保连接 TDX 时使用的本地地址为 `192.168.151.41`。
