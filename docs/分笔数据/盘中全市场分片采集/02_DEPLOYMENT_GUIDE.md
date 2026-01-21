# 02 部署指南：三节点全流程配置

## 1. 节点环境一览

| 物理机 IP | 角色 | 分片 ID | 配置文件 |
|---|---|---|---|
| 192.168.151.41 | 主控/Shard 0 | 0 | `docker-compose.node-41.yml` |
| 192.168.151.58 | Worker/Shard 1 | 1 | `docker-compose.node-58.yml` |
| 192.168.151.111 | Worker/Shard 2 | 2 | `docker-compose.node-111.yml` |

---

## 2. 关键环境变量配置

在各节点的 `docker-compose` 中，核心配置如下：

```yaml
intraday-tick-collector:
  image: get-stockdata:latest
  build:
    context: ./services/get-stockdata
    args:
      - ENABLE_PROXY=true  # 重要：允许构建时通过代理下载包
  environment:
    - SHARD_INDEX=1         # 不同节点分别设为 0, 1, 2
    - SHARD_TOTAL=3
    - REDIS_HOST=192.168.151.41
    - CONCURRENCY=64        # 并发度，全市场建议 64 以上
    - POLL_OFFSET=200       # 每次从 API 获取最近 200 条
    - POLL_INTERVAL_SECONDS=3.0
```

---

## 3. 构建与部署流程

### 第一步：代码同步 (所有节点)
```bash
git pull origin feature/redis-stream-refactor
```

### 第二步：执行部署 (Node 41)
```bash
./ops/deploy_node_41.sh
```

### 第三步：执行部署 (Node 58/111)
```bash
# 需要明确指定服务列表，脚本会自动处理 build
./ops/deploy_node_58.sh feature/redis-stream-refactor "gsd-worker,intraday-tick-collector"
```

---

## 4. 镜像构建优化
由于 `get-stockdata` 在不同节点存在依赖差异，现已改为**多阶段构建 (Multi-stage)**：
1.  **Stage 1 (base)**: 安装 Python 环境、编译器、常见依赖。
2.  **Stage 2 (final)**: 包含本地离线包 (`pytdx-1.72.tar.gz`) 安装逻辑，解决 pip 在代理模式下安装某些特定源码包失败的问题。

---

## 5. 验证命令
部署完成后，务必运行：
```bash
docker exec intraday-tick-collector hostname   # 预期: node-XX-collector
docker logs -f intraday-tick-collector           # 检查是否有 Loaded X stocks 日志
```
