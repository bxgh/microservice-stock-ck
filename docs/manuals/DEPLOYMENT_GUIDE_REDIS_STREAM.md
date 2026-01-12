# Redis Stream Tick Sync - 部署与运维手册

**版本**: 2.0 (New Architecture)
**日期**: 2026-01-13

## 1. 架构概览 (Architecture Overview)

本系统已从旧式的“静态分片”升级为 **"Redis Stream 动态抢单"** 架构。

*   **核心模式**: Producer-Consumer (生产者-消费者)。
*   **发布者 (Publisher)**: **单点运行**。负责生成全量股票任务推送到 Redis。
*   **采集者 (Worker)**: **分布式运行**。所有节点的 `mootdx-api` 服务自动作为 Worker 抢单。
*   **写入者 (Writer)**: **集中/分布式写入**。消费 `stream:tick:data` 并批量写入 ClickHouse。

### 角色分配表

| 节点 | IP | 角色 | 关键服务 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| **Node 41** | 192.168.151.41 | **Master / Publisher** | `task-orchestrator`, `redis`, `gsd-worker-consumer` | 系统大脑，运行 Redis 集群主节点 |
| **Node 111** | 192.168.151.111 | **Worker Node** | `mootdx-api` | 纯计算节点，提供算力 |
| **Node 58** | 192.168.151.58 | **Worker Node** | `mootdx-api` | 计算节点 + GitLab |

---

## 2. 部署配置 (Configuration Standards)

所有节点必须遵循以下环境变量标准，确保连接同一个 Redis Cluster。

### 2.1 环境变量 (Environment Definitions)

在所有节点的 `docker-compose.node-xx.yml` 中，`mootdx-api` 必须配置：

```yaml
    environment:
      # Redis Config (连接到 Node 41/58/111 组成的集群)
      - REDIS_HOST=192.168.151.41  # 根据实际连接调整，集群模式会自动重定向
      - REDIS_PORT=16379           # 注意：集群端口
      - REDIS_PASSWORD=            # 目前集群无密码
      - REDIS_CLUSTER=true         # 必须开启

      # Mootdx Worker Config
      - MOOTDX_CONCURRENCY=10      # 并发数
      - MOOTDX_FETCH_COUNT=5       # 每次拉取数
      
      # TDX Network (各节点必须配置自己的 Bind IP)
      - TDX_BIND_IP=192.168.151.xx # 41/58/111 各自的 IP
      - TDX_AUTO_DISCOVER=false
      - TDX_HOSTS=...              # 使用统一的高质量 IP 列表
```

### 2.2 关键变更点

1.  **TDX_BIND_IP**: 每个节点必须绑定自己的物理 IP (`192.168.151.xx`) 以利用其特殊的网络白名单。
2.  **ONE Publisher**: 只有 Node 41 的 `tasks.yml` 可以配置 `run_stream_tick.py publisher`。**严禁**在 58/111 上配置定时发布任务。

---

## 3. 部署步骤 (Deployment Steps)

### Step 1: 部署 Node 41 (Orchestrator)

1.  **更新代码**:
    ```bash
    git pull
    ```
2.  **应用配置**:
    确保 `docker-compose.node-41.yml` 中 `tasks.yml` 挂载正确，且 `gsd-worker-consumer` 已启用。
3.  **重启服务**:
    ```bash
    docker-compose -f docker-compose.node-41.yml up -d
    ```

### Step 2: 部署 Node 111 & 58 (Workers)

1.  **更新代码**:
    ```bash
    git pull
    ```
2.  **配置检查**:
    检查 `docker-compose.node-xx.yml` 的 `REDIS_CLUSTER=true` 和 `TDX_BIND_IP`。
3.  **重启服务**:
    ```bash
    docker-compose -f docker-compose.node-xx.yml up -d mootdx-api
    ```

---

## 4. 运维与监控 (Operations)

### 4.1 手动触发采集

在 **Node 41** 上执行：
```bash
# 触发 2026-01-xx 的全量采集
docker compose -f docker-compose.node-41.yml run --rm \
    gsd-worker python3 src/jobs/run_stream_tick.py publisher --date 202601xx
```

### 4.2 监控进度

使用验证脚本实时查看：
```bash
./run_verification_final.sh 202601xx
```

### 4.3 紧急重置 (Emergency Reset)

如果任务积压或数据脏乱，使用清理脚本：
```bash
# 同时清理 Redis 队列和 ClickHouse 数据
docker exec -it microservice-stock-gsd-worker-consumer-1 \
    python3 /tmp/ops_reset_env.py --date 202601xx
```

---

## 5. 故障排查 (Troubleshooting)

*   **Q: 为什么 Pending Jobs 很高但速度慢？**
    *   A: 检查 Worker 日志。可能是大量 IP 连不通导致超时。尝试缩减 `TDX_HOSTS`。
*   **Q: 为什么 ClickHouse 数据不增加？**
    *   A: 检查 `gsd-worker-consumer` (Writer) 是否存活。它是数据入库的唯一通道。
