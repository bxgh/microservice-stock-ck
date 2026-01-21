# 07 故障排除：数据流与网络通道诊断

本手册基于分布式采集系统的 **四层数据流架构**，针对可能出现的连接中断、数据丢包及系统瓶颈提供排查路径。

---

## 核心数据流拓扑
`Redis (任务下发)` -> `Collector (执行逻辑)` -> `Mootdx-API (数据网关)` -> `TDX Servers (原始数据)` -> `ClickHouse (最终存储)`

---

## 1. 第一阶段：任务领取故障 (Redis 通道)
**通道**: TCP 6379 (Node 58/111 -> Node 41)

### 现象：日志显示 `Loaded 0 stocks from Redis` 或 `ConnectionError`
*   **诊断 1**: 验证 Redis 连通性。在 Node 58/111 执行：
    `redis-cli -h 192.168.151.41 -p 6379 -a redis123 ping`
*   **诊断 2**: 检查 Redis Key。确认 `metadata:stock_codes:shard:1` 是否为空。
*   **修复**: 如果网络不通，检查 Node 41 的防火墙（ufw）是否允许 6379 端口；如果 Key 为空，执行 `daily_stock_collection` 任务。

---

## 2. 第二阶段：网关通信故障 (API 通道)
**通道**: HTTP 8003 (内部本地通信)

### 现象：Collector 日志频繁出现 `500 Server Error` 或 `Circuit Breaker is OPEN`
*   **诊断 1**: 检查 `mootdx-api` 容器状态。
    `docker ps | grep mootdx-api`
*   **诊断 2**: 查看网关健康状态。
    `curl http://localhost:8003/health`
*   **修复**: 
    - 如果 `pool.available` 长期为 0，调大 `TDX_POOL_SIZE`。
    - 如果 `status` 为 `unhealthy`，重启该节点的 `mootdx-api` 以重新触发优选 IP。

---

## 3. 第三阶段：外部溯源故障 (TDX/Proxy 通道)
**通道**: TCP 7709 (及 Proxy 12345)

### 现象：采集延迟大幅升高或 `Tick count is 0`
*   **诊断 1**: 检查代理服务状态（如使用了 Gost）。
*   **诊断 2**: 模拟请求测试。
    `curl "http://localhost:8003/api/v1/tick/000001"`
*   **修复**: 
    - 若特定 TDX IP 被封禁，需更新该节点的 `tdx_ip.md` 或重启 `mootdx-api` 刷新连接。

---

## 4. 第四阶段：入库归档故障 (ClickHouse 通道)
**通道**: TCP 9000

### 现象：日志显示 `Broken pipe` 或 `DB::Exception: Too many parts`
*   **诊断 1**: 检查磁盘空间。
    `df -h`
*   **诊断 2**: 检查 ClickHouse 错误日志。
    `docker logs microservice-stock-clickhouse --tail 100`
*   **修复**: 
    - 修改 `FLUSH_THRESHOLD`（调大）以减少合并压力。
    - 若为认证错误，核对 `.env` 中的 `CLICKHOUSE_PASSWORD`。

---

## 5. 极速诊断指令集 (Ops Cheat Sheet)

| 场景 | 命令 |
|---|---|
| **全节点连通性检查** | `ping 192.168.151.41` |
| **容器实时状态** | `docker stats intraday-tick-collector` |
| **业务逻辑报错** | `docker logs intraday-tick-collector 2>&1 | grep -i error` |
| **检查分片唯一性** | `docker exec intraday-tick-collector env | grep SHARD` |

---

## 6. 特殊情况：跨节点同步失效
若 Node 58 采集正常但 Node 41 库里看不到数据：
1.  **检查路由**: 确认 Node 58 的 `CLICKHOUSE_HOST` 是否配置为 Node 41 的真实内网 IP 而非 `127.0.0.1`。
2.  **检查时区**: 运行 `date` 确保各机器时间偏差在 1 秒以内，否则 `today()` 函数会过滤掉未来或过去的数据。
