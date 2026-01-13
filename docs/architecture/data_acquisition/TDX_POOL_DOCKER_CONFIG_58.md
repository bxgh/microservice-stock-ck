# Mootdx API 容器部署与 TDX连接池配置指南 (Server 58)

> **适用范围**: Server 58 (Worker / Shard 2)
> **服务**: `mootdx-api` (Docker 容器)
> **目的**: 确保容器能正确穿透防火墙策略，连接到高可用的 TDX 行情源。

Server 58 作为集群的核心计算节点之一，其 `mootdx-api` 部署必须遵循以下规范，确保通过专用的数据网卡 (`ens32`) 进行数据采集。

---

## 1. 核心网络概览

**必须满足的三大条件**:
1.  **Network Mode**: 必须为 `host`。
2.  **Bind IP**: 必须显式绑定 `192.168.151.58`。
3.  **Use Verified Hosts**: 必须仅连接已验证的白名单节点。

---

## 2. Docker Compose 配置规范

以下是 Server 58 专用的配置模板：

```yaml
version: '3.8'

services:
  mootdx-api:
    image: microservice-stock-mootdx-api:latest
    container_name: microservice-stock-mootdx-api
    
    # [关键配置 1] 网络模式必须为 host
    network_mode: host
    
    restart: unless-stopped
    environment:
      # [关键配置 2] 强制绑定 Server 58 数据网卡 IP
      - TDX_BIND_IP=192.168.151.58
      
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
    确认连接状态。
2.  **验证路由路径**:
    从容器发起请求，确保流量走 `ens32` 物理路径。
