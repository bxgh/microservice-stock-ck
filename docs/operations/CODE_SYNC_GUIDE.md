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


## 方法四：Webhook 自动同步 (Lightweight CI)

可以使用 Python 内置库运行一个轻量级 Webhook Server，接收 GitLab 的 Push 事件并触发本地部署脚本。

**1. 部署 Webhook 服务 (Worker 节点)**

代码已准备在 `ops/` 目录下：
- `ops/sync_deploy.sh`: 执行 git pull 和 docker build 的脚本。
- `ops/webhook_server.py`: 监听 9099 端口的 Python 服务。

**启动服务**:
```bash
# 赋予执行权限
chmod +x ops/sync_deploy.sh

# 后台启动 Webhook Server
nohup python3 ops/webhook_server.py > logs/webhook.log 2>&1 &
```

**2. 配置 GitLab (Master 节点)**

1.  进入项目仓库 -> **Settings** -> **Webhooks**。
2.  **URL**: `http://192.168.151.58:9099` (或 111)。
3.  **Secret Token**: `your-secret-token-123` (需与脚本中一致)。
4.  **Trigger**: 勾选 `Push events`。
5.  点击 **Add webhook**。

**工作原理**:
当您在 GitLab 提交代码时，GitLab 会向 Server 58 发送 POST 请求。`webhook_server.py` 收到请求后，会后台执行 `sync_deploy.sh`，完成拉取代码、重构镜像和重启服务的全过程。
