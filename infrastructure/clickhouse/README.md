# ClickHouse 3-Shard 集群部署文档

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    stock_cluster (3 Shards)                 │
├─────────────────────────────────────────────────────────────┤
│  Shard 1          │  Shard 2          │  Shard 3           │
│  Server 41        │  Server 58        │  Server 111        │
│  192.168.151.41   │  192.168.151.58   │  192.168.151.111   │
│  shard=01         │  shard=02         │  shard=03          │
│  replica=server41 │  replica=server58 │  replica=server111 │
└─────────────────────────────────────────────────────────────┘
```

**数据分布**：按 `xxHash64(stock_code)` 自动分片
- 同一只股票的所有数据存储在同一个分片
- 3 个节点并行采集和查询，性能 3x 提升

---

## 集群配置

### 节点信息

| 节点 | IP | Shard ID | Keeper ID | 角色 |
|------|----|----|-----------|------|
| Server 41 | 192.168.151.41 | 01 | 1 | Shard 1 + Keeper |
| Server 58 | 192.168.151.58 | 02 | 2 | Shard 2 + Keeper |
| Server 111 | 192.168.151.111 | 03 | 3 | Shard 3 + Keeper |

### 端口配置

| 服务 | 端口 | 用途 |
|------|------|------|
| ClickHouse TCP | 9000 | 客户端连接 |
| ClickHouse HTTP | 8123 | HTTP API |
| Keeper Client | 9181 | Keeper 客户端 |
| Keeper Raft | 9234 | Keeper 集群通信 |
| Interserver | 9009 | 节点间复制 |

### 认证信息

| 用户 | 密码 | 权限 |
|------|------|------|
| admin | admin123 | 完全访问 |
| default | (空) | 完全访问 |

---

## 数据库和表结构

### 数据库
- `stock_data` - 股票数据主库

### 表结构

#### 分笔数据（Tick Data）

**本地表**：`tick_data_local`（每个分片）
```sql
CREATE TABLE stock_data.tick_data_local (
    stock_code String,
    trade_date Date,
    tick_time String,
    price Decimal(10, 3),
    volume UInt32,
    amount Decimal(18, 2),
    direction UInt8,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, trade_date, tick_time)
TTL trade_date + INTERVAL 365 DAY;
```

**分布式表**：`tick_data`（查询/写入入口）
```sql
CREATE TABLE stock_data.tick_data (
    -- 字段同 tick_data_local
) ENGINE = Distributed('stock_cluster', 'stock_data', 'tick_data_local', xxHash64(stock_code));
```

#### K线数据（K-Line Data）

**本地表**：`stock_kline_daily_local`
```sql
CREATE TABLE stock_data.stock_kline_daily_local (
    stock_code String,
    trade_date Date,
    open_price Float64,
    high_price Float64,
    low_price Float64,
    close_price Float64,
    volume UInt64,
    amount Float64,
    turnover_rate Nullable(Float32),
    change_pct Nullable(Float32),
    update_time DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(update_time)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, trade_date);
```

**分布式表**：`stock_kline_daily`
```sql
CREATE TABLE stock_data.stock_kline_daily (
    -- 字段同 stock_kline_daily_local
) ENGINE = Distributed('stock_cluster', 'stock_data', 'stock_kline_daily_local', xxHash64(stock_code));
```

---

## 应用程序连接

### Python 示例

```python
from clickhouse_driver import Client

# 连接任意节点即可（推荐连接 Server 41）
client = Client(
    host='192.168.151.41',
    port=9000,
    user='admin',
    password='admin123',
    database='stock_data'
)

# 写入数据（使用分布式表）
client.execute("""
    INSERT INTO tick_data VALUES
    ('000001', '2026-01-09', '09:30:00', 10.5, 1000, 10500, 0, now())
""")

# 查询数据（使用分布式表）
result = client.execute("""
    SELECT * FROM tick_data 
    WHERE stock_code = '000001' 
    AND trade_date = '2026-01-09'
""")
```

### 连接字符串

```
clickhouse://admin:admin123@192.168.151.41:9000/stock_data
```

---

## 运维操作

### 启动集群

```bash
# 方式 1: 使用部署脚本（推荐）
./infrastructure/clickhouse/scripts/deploy_cluster_compose.sh

# 方式 2: 单节点启动
cd infrastructure/clickhouse
docker compose -f docker-compose.node-41.yml up -d
```

### 停止集群

```bash
./infrastructure/clickhouse/scripts/stop_cluster_compose.sh
```

### 更新配置

```bash
# 1. 编辑配置文件
vim infrastructure/clickhouse/config/users.xml

# 2. 同步并重启
./infrastructure/clickhouse/scripts/update_config.sh users.xml
```

### 健康检查

```bash
# Keeper 状态
echo mntr | nc -w 2 127.0.0.1 9181

# 集群拓扑
docker exec microservice-stock-clickhouse clickhouse-client \
  --user admin --password admin123 \
  --query "SELECT * FROM system.clusters WHERE cluster='stock_cluster'"

# 数据分布
for ip in 41 58 111; do
  echo "=== Server $ip ==="
  ssh bxgh@192.168.151.$ip \
    "docker exec microservice-stock-clickhouse clickhouse-client \
    --user admin --password admin123 \
    -q 'SELECT count() FROM stock_data.tick_data_local'"
done
```

---

## 性能特性

| 指标 | 数值 |
|------|------|
| 采集并发度 | 3x（3节点并行） |
| 查询并发度 | 3x（3节点并行） |
| 单股查询延迟 | ~10ms（单节点） |
| 全市场扫描 | 3x 加速 |
| 存储冗余 | 无（单副本） |

---

## 配置文件位置

```
infrastructure/clickhouse/
├── config/
│   ├── config.xml              # 通用配置
│   ├── users.xml               # 用户配置
│   └── config.d/
│       ├── node_41.xml         # Server 41 专用（shard=01）
│       ├── node_58.xml         # Server 58 专用（shard=02）
│       └── node_111.xml        # Server 111 专用（shard=03）
├── docker-compose.node-41.yml  # Server 41 部署
├── docker-compose.node-58.yml  # Server 58 部署
├── docker-compose.node-111.yml # Server 111 部署
└── scripts/
    ├── deploy_cluster_compose.sh   # 一键部署
    ├── stop_cluster_compose.sh     # 停止集群
    └── update_config.sh            # 更新配置
```

---

## 故障处理

### Keeper 无 Leader

```bash
# 检查所有节点 Keeper 状态
for ip in 41 58 111; do
  echo "=== Server $ip ==="
  echo mntr | ssh bxgh@192.168.151.$ip "nc -w 2 127.0.0.1 9181" | grep zk_server_state
done

# 重启集群
./infrastructure/clickhouse/scripts/deploy_cluster_compose.sh
```

### 分布式查询失败

```bash
# 检查节点间连通性
docker exec microservice-stock-clickhouse clickhouse-client \
  --user admin --password admin123 \
  --query "SELECT * FROM system.clusters WHERE cluster='stock_cluster'"

# 确认所有节点用户配置一致
for ip in 41 58 111; do
  ssh bxgh@192.168.151.$ip \
    "docker exec microservice-stock-clickhouse clickhouse-client \
    --user admin --password admin123 -q 'SELECT 1'"
done
```

### 数据倾斜

```bash
# 检查各分片数据量
for ip in 41 58 111; do
  echo "=== Server $ip ==="
  ssh bxgh@192.168.151.$ip \
    "docker exec microservice-stock-clickhouse clickhouse-client \
    --user admin --password admin123 \
    -q 'SELECT count() AS cnt, formatReadableSize(sum(data_compressed_bytes)) AS size FROM system.parts WHERE database='\''stock_data'\'' AND table='\''tick_data_local'\'''"
done
```

---

## 注意事项

1. **无副本架构**：单节点故障会导致该分片数据不可用，建议定期备份
2. **分片键选择**：使用 `stock_code` 作为分片键，确保同一股票数据在同一节点
3. **连接任意节点**：应用程序可连接任意节点，分布式表会自动路由
4. **只用分布式表**：应用程序应始终使用 `tick_data`，而非 `tick_data_local`
5. **Keeper 依赖**：虽然无数据复制，但 Keeper 仍用于集群元数据管理
