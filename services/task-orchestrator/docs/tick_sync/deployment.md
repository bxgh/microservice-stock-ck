# A股盘后补采系统分布式部署指南

## 1. 部署架构概述

```
Server 41 (主控节点)
├── task-orchestrator (Shard 0 + 数据归档)
├── gsd-worker
├── mootdx-api
└── Redis (主节点)

Server 58 (计算节点)
├── task-orchestrator (Shard 1)
├── gsd-worker
└── mootdx-api

Server 111 (计算节点)
├── task-orchestrator (Shard 2)
├── gsd-worker
└── mootdx-api
```

---

## 2. 前置条件检查

在开始部署前，确保目标服务器满足以下条件：

### 2.1 网络连通性
```bash
# 从 Server 41 测试与其他节点的连接
ping 192.168.151.58
ping 192.168.151.111

# 测试 ClickHouse 连接（端口 9000）
telnet 192.168.151.58 9000
telnet 192.168.151.111 9000
```

### 2.2 必需软件
- Docker Engine 20.10+
- Docker Compose 2.0+
- Git 2.30+

### 2.3 系统资源
- 磁盘空间: 至少 50GB 可用
- 内存: 至少 8GB
- CPU: 至少 4 核

---

## 3. 部署步骤

### 步骤 1: 代码同步

#### 在 Server 58 和 Server 111 上执行：

```bash
# 1. 切换到代码目录（如果已有旧代码）
cd /home/bxgh/microservice-stock

# 2. 拉取最新代码
git pull origin main

# 如果是首次部署，需要先克隆仓库
# git clone <repository_url> /home/bxgh/microservice-stock
# cd /home/bxgh/microservice-stock
```

---

### 步骤 2: 构建 Docker 镜像

#### 在每个节点上分别构建镜像：

```bash
# 进入项目目录
cd /home/bxgh/microservice-stock

# 构建 gsd-worker 镜像
docker build -f services/gsd-worker/Dockerfile -t gsd-worker:latest .

# 构建 task-orchestrator 镜像
docker build -f services/task-orchestrator/Dockerfile -t task-orchestrator:latest .

# 构建 mootdx-api 镜像
docker build -f services/mootdx-api/Dockerfile -t microservice-stock-mootdx-api:latest .
```

> **提示**: 如果构建速度慢，可以在 Server 41 构建好后，使用 `docker save` 和 `docker load` 传输镜像。

#### 镜像传输方式（可选）：

```bash
# 在 Server 41 上导出镜像
docker save gsd-worker:latest task-orchestrator:latest | gzip > images.tar.gz

# 传输到其他节点
scp images.tar.gz bxgh@192.168.151.58:/tmp/
scp images.tar.gz bxgh@192.168.151.111:/tmp/

# 在 Server 58 和 111 上导入镜像
docker load < /tmp/images.tar.gz
```

---

### 步骤 3: 验证配置文件

#### Server 58 关键配置检查：

```bash
# 查看 docker-compose 配置
cat docker-compose.node-58.yml | grep -A 5 "task-orchestrator"

# 确认 tasks_58.yml 存在
ls -lh services/task-orchestrator/config/tasks_58.yml
```

**预期输出**:
```yaml
task-orchestrator:
  ...
  volumes:
    - ./services/task-orchestrator/config/tasks_58.yml:/app/config/tasks.yml:ro
```

#### Server 111 关键配置检查：

```bash
# 查看 docker-compose 配置
cat docker-compose.node-111.yml | grep -A 5 "task-orchestrator"

# 确认 tasks_111.yml 存在
ls -lh services/task-orchestrator/config/tasks_111.yml
```

---

### 步骤 4: 启动服务

#### Server 58 部署：

```bash
cd /home/bxgh/microservice-stock

# 启动核心服务
docker-compose -f docker-compose.node-58.yml up -d mootdx-api
docker-compose -f docker-compose.node-58.yml up -d task-orchestrator

# 检查服务状态
docker-compose -f docker-compose.node-58.yml ps
docker logs task-orchestrator --tail 50
```

#### Server 111 部署：

```bash
cd /home/bxgh/microservice-stock

# 启动核心服务
docker-compose -f docker-compose.node-111.yml up -d mootdx-api
docker-compose -f docker-compose.node-111.yml up -d task-orchestrator

# 检查服务状态
docker-compose -f docker-compose.node-111.yml ps
docker logs task-orchestrator --tail 50
```

---

## 4. 验证部署

### 4.1 服务健康检查

```bash
# Server 58
curl http://127.0.0.1:8003/health  # mootdx-api
curl http://127.0.0.1:18000/health # task-orchestrator

# Server 111
curl http://127.0.0.1:8003/health
curl http://127.0.0.1:18000/health
```

### 4.2 手动触发测试

```bash
# 在 Server 58 上手动执行 Shard 1 采集（测试用）
docker exec -it task-orchestrator python3 /app/src/jobs/sync_tick.py \
  --scope all --shard-index 1 --shard-total 3 --date 20260113

# 在 Server 111 上手动执行 Shard 2 采集
docker exec -it task-orchestrator python3 /app/src/jobs/sync_tick.py \
  --scope all --shard-index 2 --shard-total 3 --date 20260113
```

### 4.3 定时任务验证

检查每日 15:35 的自动触发是否正常：

```bash
# 查看 task-orchestrator 日志（运行 15:35 后查看）
docker logs -f task-orchestrator | grep "daily_tick_sync"
```

### 4.4 数据完整性检查

在 Server 41 的 ClickHouse 中验证数据：

```bash
# 登录 ClickHouse
clickhouse-client

# 查询今日各分片的数据量
SELECT 
    cityHash64(stock_code) % 3 as shard,
    count(DISTINCT stock_code) as stock_count,
    count() as tick_count
FROM tick_data_intraday
WHERE trade_date = today()
GROUP BY shard
ORDER BY shard;
```

**预期输出**（示例）:
```
┌─shard─┬─stock_count─┬─tick_count─┐
│     0 │        1800 │    3500000 │
│     1 │        1800 │    3600000 │
│     2 │        1700 │    3400000 │
└───────┴─────────────┴────────────┘
```

---

## 5. 故障排查

### 问题 1: task-orchestrator 无法启动

**症状**: `docker ps` 看不到 task-orchestrator 容器

**排查**:
```bash
# 查看启动日志
docker-compose -f docker-compose.node-58.yml logs task-orchestrator

# 检查配置文件挂载
docker inspect task-orchestrator | grep -A 5 "Mounts"
```

**常见原因**: 
- `tasks_58.yml` 或 `tasks_111.yml` 文件不存在
- Docker socket 权限问题

**解决方案**:
```bash
# 确认文件存在
ls -lh services/task-orchestrator/config/tasks_*.yml

# 赋予 Docker socket 权限
sudo chmod 666 /var/run/docker.sock
```

---

### 问题 2: Redis 连接失败

**症状**: 日志中出现 `⚠️ Redis 初始化失败`

**排查**:
```bash
# 测试 Redis 连接
redis-cli -h 192.168.151.41 -p 6379 -a redis123 PING
```

**解决方案**: 确认 Server 41 的 Redis 已启动且可访问。

---

### 问题 3: ClickHouse 写入失败

**症状**: 分笔数据未写入 ClickHouse

**排查**:
```bash
# 检查 ClickHouse 连接
clickhouse-client -h 127.0.0.1 --port 9000 -u admin --password admin123

# 查看表结构
SHOW CREATE TABLE tick_data_intraday;
```

**解决方案**: 
- 确认 `tick_data_intraday` 和 `tick_data` 分布式表已创建
- 验证 ClickHouse Keeper 集群健康

---

## 6. 回滚方案

如遇严重问题需要回滚：

```bash
# 停止新服务
docker-compose -f docker-compose.node-58.yml down task-orchestrator
docker-compose -f docker-compose.node-111.yml down task-orchestrator

# 恢复到旧版本代码
git checkout <previous_commit_hash>

# 重新构建镜像
docker-compose -f docker-compose.node-58.yml build
```

---

## 7. 监控与维护

### 7.1 日志查看

```bash
# 实时日志
docker logs -f task-orchestrator

# 查看最近 100 行
docker logs task-orchestrator --tail 100
```

### 7.2 性能监控

```bash
# 查看容器资源使用
docker stats task-orchestrator gsd-worker mootdx-api
```

### 7.3 定期检查

建议设置每周检查任务：
- 检查磁盘空间
- 查看错误日志
- 验证数据完整性

---

## 8. 联系与支持

如部署过程中遇到问题，可参考：
- [实施计划](file:///home/bxgh/.gemini/antigravity/brain/229f5a14-d0b7-4c18-badf-55170446b4a5/post_market_tick_sync_plan.md)
- [交付说明](file:///home/bxgh/.gemini/antigravity/brain/229f5a14-d0b7-4c18-badf-55170446b4a5/post_market_sync_walkthrough.md)
- [代码质控报告](file:///home/bxgh/.gemini/antigravity/brain/229f5a14-d0b7-4c18-badf-55170446b4a5/code_quality_review.md)
