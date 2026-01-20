# 多节点代码同步指南

本文档说明如何在 Server 41 (GitLab Master) 提交代码后，将变更同步到 Server 58 和 Server 111 (Worker Nodes)。

## 方法一：手动同步 (Manual Sync) - **推荐**

这是目前最稳健的方式，适用于无 CI/CD 流水线环境。

**步骤 1：在 Server 41 提交代码**
```bash
# 在本地开发机或 Server 41
git add .
git commit -m "feat: your feature"
git push origin feature/your-branch
```

**步骤 2：登录 Worker 节点 (Server 58 / 111)**
```bash
ssh root@192.168.151.58
# 或
ssh root@192.168.151.111
```

**步骤 3：拉取代码并重构**
```bash
cd /home/bxgh/microservice-stock

# 1. 拉取最新代码
git pull origin feature/your-branch

# 2. 重构受影响的服务 (例如 gsd-worker, mootdx-api)
# 注意：必须在根目录执行 build 以包含 libs/ 依赖
docker build -t gsd-worker:latest -f services/gsd-worker/Dockerfile .
# 如果修改了 task-orchestrator
docker build -t task-orchestrator:latest -f services/task-orchestrator/Dockerfile . --build-arg ENABLE_PROXY=true --build-arg PROXY_URL=http://192.168.151.18:3128

# 3. 重启服务
# 适用于 Poller
docker restart gsd-shard-poller

# 适用于 gsd-worker (如果是常驻服务)
docker compose -f docker-compose.node-58.yml up -d gsd-worker
```

## 方法二：自动脚本同步 (Scripted Sync)

为了简化操作，可以在 Worker 节点创建一个同步脚本 `sync_deploy.sh`。

**创建脚本**: `/home/bxgh/microservice-stock/sync_deploy.sh`
```bash
#!/bin/bash
set -e

BRANCH=${1:-"main"}

echo ">> 1. Pulling code from $BRANCH..."
git fetch
git checkout $BRANCH
git pull origin $BRANCH

echo ">> 2. Rebuilding Images..."
# 这里列出核心服务的构建命令
docker build -t gsd-worker:latest -f services/gsd-worker/Dockerfile .
docker build -t task-orchestrator:latest -f services/task-orchestrator/Dockerfile . --build-arg ENABLE_PROXY=true --build-arg PROXY_URL=http://192.168.151.18:3128

echo ">> 3. Restarting Services..."
if [ "$(docker ps -q -f name=gsd-shard-poller)" ]; then
    docker restart gsd-shard-poller
fi

echo ">> Done!"
```

**使用方法**:
```bash
# 一键同步并部署
./sync_deploy.sh feature/redis-stream-refactor
```

## 方法三：GitLab CI/CD (自动化)

*需要配置 GitLab Runner，暂未部署。*


## 方法四：Webhook 智能同步 (Smart Sync) - **已部署**

可以使用 Python 内置库运行一个轻量级 Webhook Server，接收 GitLab 的 Push 事件并触发本地部署脚本。
**2026-01-20 更新**: 现在的 Webhook 服务具备**智能感知**能力，支持动态分支和按需部署。

**1. 部署架构 (Worker 节点)**

代码已位于 `ops/` 目录下：
- `ops/webhook_server.py`: 监听 9099 端口的 Python 服务 (Systemd 托管)。
- `ops/deploy_node_58.sh`: Server 58 专用智能部署脚本 (支持参数控制)。
- `ops/deploy_node_111.sh`: Server 111 专用智能部署脚本。

**2. 智能工作流程**

1.  **代码提交**: 开发者 push 代码到 GitLab（任意分支）。
2.  **Webhook 触发**: GitLab 发送 payload 到 `webhook_server.py`。
3.  **智能分析**: Python 脚本解析 payload：
    - **提取分支名**: 自动识别 `ref` 字段（如 `feature/xxx`）。
    - **分析变更路径**: 识别哪些文件发生了变化。
    - **匹配服务**: 根据预定义的映射表，决定需要重启哪些容器。
        - 仅修改文档/非核心代码 → **只同步代码，不重启任何服务**。
        - 修改 `services/mootdx-api` → **只重启 mootdx-api**。
        - 修改 `libs/gsd-shared` → **重启相关的所有服务**。
4.  **精准执行**: 调用部署脚本（如 `deploy_node_58.sh`），传入分支名和服务列表，执行最小化更新。

**3. 配置 GitLab (Master 节点)**

1.  进入项目仓库 -> **Settings** -> **Webhooks**。
2.  **URL**: `http://192.168.151.58:9099` (或 111)。
3.  **Secret Token**: `123456`。
4.  **Trigger**: 勾选 `Push events`。
5.  点击 **Add webhook**。

**4. 服务管理 (Systemd)**:

```bash
# 查看服务状态
sudo systemctl status webhook-server

# 查看实时日志 (观察智能部署决策)
journalctl -u webhook-server -f

# 手动重启服务 (更新 webhook 代码后执行)
sudo systemctl restart webhook-server
```

**5. 路径映射规则 (webhook_server.py)**

| 变更路径 | 影响的服务 |
|----------|------------|
| `services/mootdx-api/*` | mootdx-api |
| `services/mootdx-source/*` | mootdx-source |
| `services/gsd-worker/*` | gsd-worker |
| `services/task-orchestrator/*` | shard-poller, task-orchestrator |
| `libs/gsd-shared/*` | mootdx-api, gsd-worker, task-orchestrator |
| `docker-compose*`, `Dockerfile` | **全量部署** |

