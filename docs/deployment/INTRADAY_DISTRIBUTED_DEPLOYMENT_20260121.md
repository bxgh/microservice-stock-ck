# 盘中实时采集全市场扩展部署文档

**文档版本**: 1.0  
**创建日期**: 2026-01-21  
**作者**: 系统架构师  
**状态**: ✅ Node 41 已完成，Node 58/111 待部署

---

## 一、改造概览

### 改造目标
将 `intraday-tick-collector` 从 **HS300 单机采集** 扩展为 **全市场分布式采集**。

| 维度 | 改造前 | 改造后 |
|------|--------|--------|
| 股票池 | HS300 (~300只) | 全市场 (~5800只) |
| 节点数 | 1 (Server 41) | 3 (41, 58, 111) |
| 数据源 | YAML 静态文件 | Redis 动态分片 |
| 每节点负载 | 300 只 | ~1933 只 |
| 并发数 | 32 | 64 |
| 采集周期 | 2s | 3s |

---

## 二、架构设计

### 分片策略
```
Redis (Server 41:6379)
├── metadata:stock_codes:shard:0 → 1942 只 (Node 41)
├── metadata:stock_codes:shard:1 → 1925 只 (Node 58)
└── metadata:stock_codes:shard:2 → 1934 只 (Node 111)
```

**分片算法**: `xxHash64(stock_code) % 3` (与 ClickHouse Distributed 一致)

### 数据流
```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Node 41    │   │  Node 58    │   │  Node 111   │
│  Shard 0    │   │  Shard 1    │   │  Shard 2    │
│  1942 只    │   │  1925 只    │   │  1934 只    │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
              ┌──────────────────┐
              │   ClickHouse     │
              │ tick_data_intraday│
              └──────────────────┘
```

---

## 三、代码改造清单

### 1. 核心改动

**文件**: `services/get-stockdata/src/core/collector/intraday_tick_collector.py`

#### 新增依赖
```python
import redis.asyncio as aioredis
```

#### 新增环境变量常量
```python
SHARD_INDEX = int(os.getenv("SHARD_INDEX", "0"))
SHARD_TOTAL = int(os.getenv("SHARD_TOTAL", "1"))  # 1=单机模式, >1=分布式模式
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "redis123")
REDIS_SHARD_KEY_PREFIX = "metadata:stock_codes:shard"
```

#### 新增方法
- `_load_stock_pool_from_redis()`: 从 Redis 加载分片股票池
- `_load_stock_pool_from_yaml()`: 保留原有 YAML 加载逻辑

#### 智能路由逻辑
```python
async def _load_stock_pool(self):
    if self.shard_total > 1:
        await self._load_stock_pool_from_redis()  # 分布式模式
    else:
        await self._load_stock_pool_from_yaml()   # 单机模式
```

---

## 四、配置文件变更

### Node 41 (`docker-compose.node-41.yml`)

```yaml
intraday-tick-collector:
  environment:
    # 分布式采集配置
    - SHARD_INDEX=0
    - SHARD_TOTAL=3
    - REDIS_HOST=127.0.0.1
    - REDIS_PORT=6379
    - REDIS_PASSWORD=redis123
    # 性能调优参数
    - CONCURRENCY=64
    - FLUSH_THRESHOLD=3000
    - POLL_INTERVAL_SECONDS=3.0
    - POLL_OFFSET=200
```

### Node 58 (`docker-compose.node-58.yml`)

```yaml
intraday-tick-collector:
  environment:
    # 分布式采集配置
    - SHARD_INDEX=1
    - SHARD_TOTAL=3
    - REDIS_HOST=192.168.151.41  # 远程 Redis
    - REDIS_PORT=6379
    - REDIS_PASSWORD=redis123
    # 性能调优参数
    - CONCURRENCY=64
    - FLUSH_THRESHOLD=3000
    - POLL_INTERVAL_SECONDS=3.0
    - POLL_OFFSET=200
```

### Node 111 (`docker-compose.node-111.yml`)

```yaml
intraday-tick-collector:
  environment:
    # 分布式采集配置
    - SHARD_INDEX=2
    - SHARD_TOTAL=3
    - REDIS_HOST=192.168.151.41  # 远程 Redis
    - REDIS_PORT=6379
    - REDIS_PASSWORD=redis123
    # 性能调优参数
    - CONCURRENCY=64
    - FLUSH_THRESHOLD=3000
    - POLL_INTERVAL_SECONDS=3.0
    - POLL_OFFSET=200
```

---

## 五、部署步骤

### Phase 1: Node 41 (已完成 ✅)

```bash
# 1. 重启容器
cd /home/bxgh/microservice-stock
docker compose -f docker-compose.node-41.yml up -d intraday-tick-collector

# 2. 验证日志
docker logs intraday-tick-collector --tail 50

# 预期输出:
# ✅ Redis connected (127.0.0.1:6379)
# ✅ Loaded 1942 stocks from Redis (分布式模式, Shard 0/3)
# 💾 Flushed XXXXX ticks to ClickHouse
```

**验证结果**:
- ✅ Redis 连接成功
- ✅ 从 Redis 加载 1942 只股票 (Shard 0)
- ✅ 首次刷盘写入 323,006 条 Tick
- ✅ 正常轮次写入 11,061 条 Tick (约 48 秒)

### Phase 2: Node 58 (待部署)

```bash
# 在 Server 58 上执行:
cd /home/bxgh/microservice-stock

# 1. 拉取最新代码
git pull origin main

# 2. 重新构建镜像 (如果代码有更新)
docker compose -f docker-compose.node-58.yml build get-stockdata

# 3. 启动容器
docker compose -f docker-compose.node-58.yml up -d intraday-tick-collector

# 4. 验证日志
docker logs intraday-tick-collector --tail 50
```

**预期输出**:
```
✅ Loaded 1925 stocks from Redis (分布式模式, Shard 1/3)
```

### Phase 3: Node 111 (待部署)

```bash
# 在 Server 111 上执行:
cd /home/bxgh/microservice-stock

# 1. 拉取最新代码
git pull origin main

# 2. 重新构建镜像
docker compose -f docker-compose.node-111.yml build get-stockdata

# 3. 启动容器
docker compose -f docker-compose.node-111.yml up -d intraday-tick-collector

# 4. 验证日志
docker logs intraday-tick-collector --tail 50
```

**预期输出**:
```
✅ Loaded 1934 stocks from Redis (分布式模式, Shard 2/3)
```

---

## 六、验证清单

### 1. 分片完整性验证

```bash
# 在 Node 41 执行
docker exec node-41-redis redis-cli -a redis123 scard metadata:stock_codes:shard:0
# 预期: 1942

docker exec node-41-redis redis-cli -a redis123 scard metadata:stock_codes:shard:1
# 预期: 1925

docker exec node-41-redis redis-cli -a redis123 scard metadata:stock_codes:shard:2
# 预期: 1934

# 总和: 1942 + 1925 + 1934 = 5801 ✓
```

### 2. ClickHouse 数据验证

```sql
-- 查询今日各 Shard 写入量
SELECT 
    hostName() as shard,
    count() as tick_count,
    count(DISTINCT stock_code) as stock_count
FROM tick_data_intraday
WHERE trade_date = today()
GROUP BY shard
ORDER BY shard;
```

**预期结果** (运行 10 分钟后):
| shard | tick_count | stock_count |
|-------|-----------|-------------|
| node-41 | ~50,000 | ~1,942 |
| node-58 | ~48,000 | ~1,925 |
| node-111 | ~49,000 | ~1,934 |

### 3. 性能监控

```bash
# 各节点 CPU 使用率
while true; do
  echo "=== $(date) ==="
  ssh root@192.168.151.41 "docker stats intraday-tick-collector --no-stream --format 'Node 41: CPU {{.CPUPerc}} MEM {{.MemUsage}}'"
  ssh root@192.168.151.58 "docker stats intraday-tick-collector --no-stream --format 'Node 58: CPU {{.CPUPerc}} MEM {{.MemUsage}}'"
  ssh root@192.168.151.111 "docker stats intraday-tick-collector --no-stream --format 'Node 111: CPU {{.CPUPerc}} MEM {{.MemUsage}}'"
  sleep 10
done
```

**预期性能**:
- CPU: 10-30% (单核)
- 内存: 200-500MB
- 网络: 1-5 Mbps

---

## 七、性能对比

| 指标 | 单机 HS300 | 分布式全市场 |
|------|-----------|------------|
| 总股票数 | 300 | 5800 |
| 单轮采集时间 | <1s | 1.5-2s |
| CPU 占用 (单核) | 5-10% | 10-30% |
| 内存占用 | 150MB | 400MB |
| 每轮写入量 | 5,000 条 | 10,000+ 条 |
| MD5 计算次数 | 6万次 | 39万次 (分3节点) |

---

## 八、故障排查

### 问题 1: Redis 连接失败

**现象**:
```
❌ Failed to load stock pool from Redis: Connection refused
```

**排查**:
```bash
# 1. 检查 Redis 可达性
telnet 192.168.151.41 6379

# 2. 检查防火墙
sudo iptables -L | grep 6379

# 3. 检查 Redis 配置
docker exec node-41-redis redis-cli -a redis123 CONFIG GET bind
```

**解决**:
```bash
# 开放 Redis 端口 (如需要)
sudo iptables -I INPUT -p tcp --dport 6379 -j ACCEPT
```

### 问题 2: 分片 Key 为空

**现象**:
```
ValueError: Shard key metadata:stock_codes:shard:1 is empty or not found
```

**排查**:
```bash
# 检查 daily_stock_collection 任务是否执行
docker logs task-orchestrator | grep daily_stock_collection
```

**解决**:
```bash
# 手动触发股票代码采集
docker compose -f docker-compose.node-41.yml run --rm gsd-worker python -m jobs.daily_stock_collection
```

### 问题 3: ClickHouse 写入权限错误

**现象**:
```
❌ Failed to write to ClickHouse: ACCESS_DENIED
```

**排查**:
```bash
# 测试 ClickHouse 连接
echo "SELECT 1" | curl 'http://127.0.0.1:8123/?user=admin&password=admin123' --data-binary @-
```

---

## 九、回滚方案

如需回滚到单机 HS300 模式:

```yaml
# docker-compose.node-41.yml
intraday-tick-collector:
  environment:
    - SHARD_TOTAL=1  # 关键：设为 1 启用单机模式
    - STOCK_POOL_PATH=/app/config/hs300_stocks.yaml
    - CONCURRENCY=32
```

---

## 十、后续优化方向

1. **动态扩缩容**: 支持运行时调整 `SHARD_TOTAL`
2. **自动故障转移**: 某节点故障时，其他节点接管分片
3. **实时监控面板**: Grafana 展示三节点采集状态
4. **智能限流**: 根据 TDX 服务器负载动态调整并发

---

## 附录：关键指标

### 当前配置 (分布式模式)

| 参数 | 值 | 说明 |
|------|-----|------|
| SHARD_TOTAL | 3 | 3 节点分片 |
| CONCURRENCY | 64 | HTTP 并发数 |
| FLUSH_THRESHOLD | 3000 | 批量写入阈值 |
| POLL_INTERVAL_SECONDS | 3.0 | 轮询周期 |
| POLL_OFFSET | 200 | 每次拉取条数 |

### 实测数据 (Node 41, 2026-01-21 10:54)

- 启动后首次刷盘: **323,006 条** (历史积压)
- 正常轮次刷盘: **11,061 条** (48 秒)
- 加载股票数: **1,942 只**
- Redis 连接延迟: **<10ms**

---

**文档结束**
