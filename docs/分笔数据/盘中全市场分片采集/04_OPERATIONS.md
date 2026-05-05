# 04 运维监控：状态检查与故障排查

## 1. 实时健康检查 (Node 41)

### 查看实时数据吞吐量
每 10 秒刷新一次，观察数据是否持续入库：
```bash
watch -n 10 "docker exec microservice-stock-clickhouse clickhouse-client \
--user admin --password admin123 \
--query \"SELECT count() FROM stock_data.tick_data_intraday WHERE created_at >= now() - INTERVAL 1 MINUTE\""
```

### 检查分片均衡度
由于三节点主机名已区分，可以运行：
```bash
docker exec microservice-stock-clickhouse clickhouse-client --user admin --password admin123 --query "
SELECT hostName(), count() 
FROM stock_data.tick_data_intraday 
WHERE trade_date = today() 
GROUP BY hostName()"
```

---

## 2. 常见故障处理

### 问题 A: 采集器加载 0 只股票
*   **现象**: 日志显示 `Loaded 0 stocks from Redis`。
*   **原因**: 中心 Redis 分片数据未生成或 Key 设置错误。
*   **解决**: 在 Node 41 运行 `python -m jobs.daily_stock_collection` 重建分片。

### 问题 B: 构建时 pip 下载失败
*   **现象**: Docker build 报错 `pip: No matching distribution found`。
*   **原因**: 环境变量中的代理地址不可达或 pip 源（阿里云/清华大学）连接超时。
*   **解决**: 检查物理机 `http://192.168.151.18:3128` 是否通畅，或者修改 `Dockerfile` 中的 pip 定向。

---

## 3. 日常巡检清单
1.  **磁盘空间**: 检查 `/var/lib/docker/volumes`，分笔数据每天约产生 GB 级数据。
2.  **Redis 状态**: `redis-cli info memory` 检查是否超过内存封顶。
3.  **时钟同步**: 确保三节点物理机 `ntp` 时间一致，否则 `created_at` 字段会导致数据统计混乱。
