# Server 41 Docker 环境与网络连通性修复报告

**日期**: 2026-01-11
**作者**: AI Assistant (Antigravity)
**状态**: ✅ 已解决

## 1. 问题背景

在 Server 41 (主控节点) 上重新构建和启动微服务集群时，遇到了以下主要问题：

1.  **Docker 构建失败**: 在构建镜像时，由于网络代理对 HTTPS Tunnel 的支持不稳定，导致 `pip install` 和 `apt-get` 频繁报 `503 Service Unavailable` 错误，无法下载依赖包。
2.  **配置不一致**: `docker-compose.node-41.yml` 的配置（如构建上下文、Redis/Prometheus 容器命名）与 Server 111 的已验证模版不一致，导致服务启动冲突或挂载失败。
3.  **TDX 连通性未知**: 需要验证 Server 41 对于不同电信/联通线路 TDX 行情服务器的连通性，以筛选出最佳节点列表。
4.  **Git 代码冲突**: 本地针对 Server 41 的大量修改与远程仓库存在版本冲突，阻碍了代码同步。

## 2. 修复过程

### 2.1 网络代理与 Docker 构建优化

为解决 `503 Service Unavailable` 错误，采取了"降级为 HTTP 镜像源"的策略，绕过 HTTPS 透明代理的限制。

*   **Dockerfile 修改**:
    *   将 `mootdx-source` 和 `quant-strategy` 的 Dockerfile 中的 PyPI 源从 `https://pypi.tuna.tsinghua.edu.cn` 修改为 `http://mirrors.aliyun.com` (阿里云 HTTP 源)。
    *   在 `pip.conf` 中添加 `trusted-host = mirrors.aliyun.com` 以信任 HTTP 源。
    *   在构建命令中显式传递 `ENABLE_PROXY=true` 和 `PROXY_URL` 参数。
*   **构建上下文统一**:
    *   将所有服务的 `build.context` 统一调整为项目根目录 `.`，解决 `libs/gsd-shared` 等共享库无法复制的问题。

### 2.2 Docker Compose 配置重构

参考已在 Server 111 验证通过的配置，重构了 `docker-compose.node-41.yml`：

*   **容器隔离**: 将基础组件重命名为 `node-41-redis` 和 `node-41-prometheus`，防止与系统级或其他项目的容器产生命名冲突。
*   **端口调整**: Prometheus 宿主机端口调整为 `9091` (原 9090 被系统占用)。
*   **网络绑定**: 设置 `TDX_BIND_IP=192.168.151.41`，强制通达信流量走指定的物理网卡 (ens32)。
*   **配置挂载**: 修复了 Prometheus 配置文件挂载报错的问题，确保配置目录结构正确。

### 2.3 TDX 连通性验证

在修复后的 `mootdx-api` 容器中集成诊断工具，并执行了连接测试：

*   **工具集成**: 在 `Dockerfile` 中增加 `COPY services/mootdx-api/diagnostics/ ./diagnostics/`。
*   **测试结果** (运行 `serial_test_v2.py`):
    *   ✅ `175.6.5.153` (深圳电信) - 58.29ms
    *   ✅ `139.9.51.18` (广州电信) - 160.33ms
    *   ✅ `139.159.239.163` (广州电信) - 170.14ms
    *   ✅ `139.9.133.247` (广州电信) - 193.24ms
*   **结论**: 所有预设节点均可正常连接，无需配置复杂的 iptables 转发规则。

### 2.4 Git 冲突解决与同步

*   **冲突解决**: 手动修复了 `docker-compose.node-58.yml` 和 `services/mootdx-api/Dockerfile` 中的合并冲突，保留了本地的路径优化。
*   **代码同步**: 成功执行 `Merge` 并推送到远程 `feature/quant-strategy` 分支，实现了全集群代码库的一致性。

## 3. 当前系统状态

| 服务名称 | 状态 | 说明 |
| :--- | :--- | :--- |
| **mootdx-api** | ✅ Healthy | 版本 `latest`, 端口 `8003`, 连接池正常 (3/3 节点) |
| **mootdx-source** | ✅ Running | 依赖 mootdx-api, gRPC 端口 `50051` |
| **task-orchestrator**| ✅ Running | 任务调度服务正常 |
| **gsd-worker** | ✅ Running | 分片采集 Worker 就绪 |
| **quant-strategy** | ✅ Running | 策略引擎 (Dev模式) 启动 |
| **node-41-redis** | ✅ Running | 端口 `6379`, 独立运行 |
| **node-41-prometheus**| ✅ Running | 端口 `9091`, 监控正常 |

## 4. 后续建议

1.  **监控告警**: 利用部署好的 Prometheus 配置 Grafana 仪表盘，监控连接池状态。
2.  **定期测试**: 建议将 `diagnostics/serial_test_v2.py` 加入定时任务，每天开盘前自动验证节点质量。
3.  **镜像固化**: 尽快在 CI/CD 流水线中固化当前修复后的 Dockerfile，推送到私有仓库。
