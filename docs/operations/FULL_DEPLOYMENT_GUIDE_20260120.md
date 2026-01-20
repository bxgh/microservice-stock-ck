# 全服务器完整部署流程指南 (2026-01-20)

本文档基于最新架构和 `feature/redis-stream-refactor` 分支，梳理了 Server 41, 58, 111 的完整部署流程。

## 1. 核心架构回顾

| 节点 | IP | 角色 | 关键组件 | 部署脚本 |
|---|---|---|---|---|
| **Server 41** | `192.168.151.41` | **主控/开发** | Orchestrator, Redis(M1), CH(S1) | `ops/deploy_node_41.sh` |
| **Server 58** | `192.168.151.58` | **Worker/GitLab** | GitLab, Redis(M2), CH(S2), **三网卡** | `ops/deploy_node_58.sh` |
| **Server 111** | `192.168.151.111` | **Worker** | Redis(M3), CH(S3) | `ops/deploy_node_111.sh` |

---

## 2. Server 41 部署流程 (主控节点)

**特点**: 作为开发机，代码通常为本地最新，**不需要** `git pull`。

### 方式 A: 智能部署 (推荐)
根据代码变更自动决定需要重建的服务，避免全量构建：
```bash
cd /home/bxgh/microservice-stock
./ops/smart_deploy.sh
```

**工作原理**:
- 对比上次部署的 commit 和当前 HEAD
- 仅重建受影响的服务 (如修改了 `services/mootdx-api/` 则只重建 `mootdx-api`)
- 修改了 `libs/gsd-shared/` 会触发所有依赖服务重建

### 方式 B: 全量部署
重建所有业务服务（耗时较长）：
```bash
./ops/deploy_node_41.sh
```

### 方式 C: 单服务部署
仅重建指定服务：
```bash
docker compose -f docker-compose.node-41.yml up -d --build mootdx-api
# 或多个
docker compose -f docker-compose.node-41.yml up -d --build task-orchestrator quant-strategy
```

### 验证
- 检查调度器日志: `docker logs -f task-orchestrator`
- 检查 API: `curl http://localhost:8003/health`

---

## 3. Server 58 部署流程 (Worker 节点)

**特点**: 需要三网卡特殊网络配置，托管 GitLab。

### 前置条件: 网络配置
如果服务器刚重启，需确保三网卡路由规则生效（通常开机自启，若网络异常请检查）：
```bash
# 验证网卡状态
ip route show
# 若需重新配置，请参考: docs/operations/SERVER_58_TRIPLE_NIC_DEPLOYMENT.md
# /home/bxgh/microservice-stock/deploy-triple-nic.sh
```

### 应用部署步骤
1.  **登录服务器**:
    ```bash
    ssh root@192.168.151.58
    ```
2.  **确认环境配置**:
    ```bash
    cat /home/bxgh/microservice-stock/.env
    # 确保: SHARD_INDEX=1
    ```
3.  **获取最新脚本 (首次)**:
    - 如果 `ops/deploy_node_58.sh` 尚未同步过去，需手动 scp 或 git pull 一次。
4.  **执行部署**:
    ```bash
    cd /home/bxgh/microservice-stock
    # 该脚本会强制拉取 feature/redis-stream-refactor 分支
    ./ops/deploy_node_58.sh
    ```
5.  **验证**:
    - `docker ps | grep gsd-worker`

---

## 4. Server 111 部署流程 (Worker 节点)

**特点**: 标准计算节点。

### 步骤
1.  **登录服务器**:
    ```bash
    ssh root@192.168.151.111
    ```
2.  **确认环境配置**:
    ```bash
    cat /home/bxgh/microservice-stock/.env
    # 确保: SHARD_INDEX=2
    ```
3.  **执行部署**:
    ```bash
    cd /home/bxgh/microservice-stock
    # 该脚本会强制拉取 feature/redis-stream-refactor 分支
    ./ops/deploy_node_111.sh
    ```
4.  **验证**:
    - `docker ps | grep gsd-worker`

---

## 5. 故障排查

- **Git 拉取失败**: 检查 Server 58/111 到 GitLab (Server 58:8800) 的连通性。
- **构建慢/失败**: Server 41 构建脚本内置了代理参数；Server 58/111 若构建失败，可能需要检查各节点的 Docker 代理配置 (`~/.docker/config.json` 或 `dockerd` 环境变量)。
