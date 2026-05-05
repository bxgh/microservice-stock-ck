# ClickHouse 集群快速参考

## 一键命令

```bash
# 启动集群
./infrastructure/clickhouse/scripts/deploy_cluster_compose.sh

# 停止集群
./infrastructure/clickhouse/scripts/stop_cluster_compose.sh

# 更新配置
./infrastructure/clickhouse/scripts/update_config.sh <配置文件名>

# 健康检查
echo mntr | nc -w 2 127.0.0.1 9181
```

---

## 连接信息

| 项目 | 值 |
|------|-----|
| 主机 | 192.168.151.41（任意节点均可） |
| 端口 | 9000 (TCP) / 8123 (HTTP) |
| 用户 | admin |
| 密码 | admin123 |
| 数据库 | stock_data |

**连接字符串**：
```
clickhouse://admin:admin123@192.168.151.41:9000/stock_data
```

---

## 表使用

### 写入数据
```sql
-- 使用分布式表（自动分片）
INSERT INTO stock_data.tick_data VALUES 
  ('000001', '2026-01-09', '09:30:00', 10.5, 1000, 10500, 0, now());
```

### 查询数据
```sql
-- 使用分布式表（自动汇总）
SELECT * FROM stock_data.tick_data 
WHERE stock_code = '000001' 
ORDER BY trade_date, tick_time;
```

### 表列表
| 表名 | 类型 | 用途 |
|------|------|------|
| `tick_data` | 分布式 | **应用程序使用此表** |
| `tick_data_local` | 本地 | 内部存储，勿直接使用 |
| `stock_kline_daily` | 分布式 | **应用程序使用此表** |
| `stock_kline_daily_local` | 本地 | 内部存储，勿直接使用 |

---

## 集群拓扑

```
Server 41 (Shard 01) ─┐
Server 58 (Shard 02) ─┼─ 3 Shards, 按 stock_code hash 分片
Server 111 (Shard 03) ┘
```

**分片策略**：`xxHash64(stock_code)`
- 同一股票的所有数据在同一节点
- 3 节点并行采集和查询

---

## 常用诊断

```bash
# 查看集群状态
docker exec microservice-stock-clickhouse clickhouse-client \
  --user admin --password admin123 \
  --query "SELECT * FROM system.clusters WHERE cluster='stock_cluster'"

# 查看各节点数据量
for ip in 41 58 111; do
  echo "=== Server $ip ==="
  ssh bxgh@192.168.151.$ip \
    "docker exec microservice-stock-clickhouse clickhouse-client \
    --user admin --password admin123 \
    -q 'SELECT count() FROM stock_data.tick_data_local'"
done

# 查看 Keeper 状态
echo mntr | nc -w 2 127.0.0.1 9181 | grep -E "zk_server_state|zk_synced_followers"
```

---

## Python 连接示例

```python
from clickhouse_driver import Client

client = Client(
    host='192.168.151.41',
    user='admin',
    password='admin123',
    database='stock_data'
)

# 写入
client.execute("INSERT INTO tick_data VALUES (...)")

# 查询
result = client.execute("SELECT * FROM tick_data WHERE ...")
```

---

## 重要提醒

1. ✅ **应用程序只使用分布式表**（`tick_data`, `stock_kline_daily`）
2. ✅ **连接任意节点均可**（推荐 Server 41）
3. ✅ **数据自动分片**，无需手动指定分片
4. ⚠️ **无副本架构**，建议定期备份
5. ⚠️ **不要直接操作本地表**（`*_local`）

详细文档：`infrastructure/clickhouse/README.md`
