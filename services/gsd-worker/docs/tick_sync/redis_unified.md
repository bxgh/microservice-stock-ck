# Redis 端口统一方案 (迁移至 6379)

## 方案目标
将所有服务（mootdx-api, gsd-worker, task-orchestrator 等）的 Redis 连接统一指向 **Server 41 的 6379 端口**（带密码 `redis123`），并关停目前占用的 16379 端口（原有集群模式实例）。

## 变更内容

### 1. 关停并清理 16379 端口实例
- 在 Server 41 (及 58/111) 上停止并移除名为 `microservice-stock-redis` 的容器。
- 移除宿主机上对应的 `infrastructure/redis/node-41/docker-compose.yml` 相关服务。

### 2. 更新 Docker Compose 配置
- **Server 41**: [docker-compose.node-41.yml](file:///home/bxgh/microservice-stock/docker-compose.node-41.yml)
  - 确认所有服务环境变量使用 `REDIS_PORT=6379`, `REDIS_PASSWORD=redis123`, `REDIS_CLUSTER=false`。
- **Server 58**: [docker-compose.node-58.yml](file:///home/bxgh/microservice-stock/docker-compose.node-58.yml)
  - [NEW] 为 Node 58 补全 `task-orchestrator` 服务定义。
  - 更新所有服务连接至 `192.168.151.41:6379`。
- **Server 111**: [docker-compose.node-111.yml](file:///home/bxgh/microservice-stock/docker-compose.node-111.yml)
  - 更新所有服务连接至 `192.168.151.41:6379`。

### 3. 更新任务调度配置 (Task Orchestrator)
- **tasks.yml** / **tasks_58.yml** / **tasks_111.yml**:
  - 全局或任务级环境变量统一修正为 `6379` 端口。
  - 显式添加 `REDIS_PASSWORD: "redis123"`。
  - 设置 `REDIS_CLUSTER: "false"`。

### 4. 更新辅助脚本
- `deploy_remote_nodes.sh`: 修正远程节点 `.env` 生成逻辑。
- `run_verification_final.sh`: 修正测试代码中的 Redis 连接信息。
- `ops_reset_env.py` / `clean_redis.py`: 修正默认端口。

---

## 验证计划

### 自动化验证
1. **连通性测试**:
   - 在 Server 58/111 运行 `redis-cli -h 192.168.151.41 -p 6379 -a redis123 PING` 确保互通。
2. **状态写入验证**:
   - 触发一次补采任务，验证状态写入到 6379 端口而非 16379。

### 手动验证
- 观察三个节点的 `task-orchestrator` 日志，确认无 `Connection Error` 报错。
- 确认不再能通过 `16379` 端口连接 Redis。
