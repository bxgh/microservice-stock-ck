# 分笔数据采集策略与并发指南

> **版本**: v1.1  
> **更新时间**: 2026-01-17  
> **文档说明**: 本文档记录了 `gsd-worker` 与 `mootdx-api` 协同工作的分布式分笔数据采集实现细节、并发对齐原则及搜索矩阵策略。

---

## 0. 背景与挑战

中国 A 股全市场分笔成交数据（Tick Data）是量化高频策略的核心输入，但其采集面临以下技术瓶颈：

1. **协议限制**: 通达信 (TDX) 协议单次请求最多返回 5000 条数据，而热门股票全天成交可达数万笔，必须多次、多区间请求才能覆盖全天。
2. **数据源限流**: 单个 TDX 节点对并发连接和请求频率有严格限制。单 IP 并发过高会触发行情源封禁。
3. **防火墙深度检测 (DPI)**: 生产环境网络常对 TCP 7709 端口实施 DPI。由于 TDX 协议是非标准协议，容器网络（Bridge 模式）发出的包常被判定为非法连接。
4. **时效性要求**: 全市场 5000+ 只股票的数据必须在盘后极短时间内（如 2 小时内）完成同步、清洗并入库 ClickHouse，以供晚间策略复盘。

本指南记录的“分布式 + 连接池 + 搜索矩阵”架构，正是为了系统性解决上述挑战。

---

## 1. 架构概览

系统采用 **分布式分片采集架构**，通过 3 个节点并行处理全市场（约 5300+ 只股票）的分笔数据。

### 1.1 协同模型
- **mootdx-api**: 数据网关，维护 TDX 连接池，负责协议级并发安全。
- **gsd-worker**: 任务执行器，负责业务逻辑、质量筛选、重试及存储。
- **task-orchestrator**: 调度器，负责分发分片任务及工作流编排。

---

## 2. 并发对齐原则 (Critical)

为了达到性能最优化并防止资源浪费或排队阻塞，系统遵循以下公式：

> **`GSD_WORKER_CONCURRENCY` (采集并发) = `TDX_POOL_SIZE` (连接池大小)**

### 2.1 为什么需要对齐？
- **不一致的风险**:
    - `Worker > Pool`: 产生应用层排队。Worker 会在 API 端阻塞，占用 Worker 协程资源，且可能导致 HTTP 超时。
    - `Worker < Pool`: 资源闲置。连接池中昂贵的 TDX 连接未被充分利用，采集速度变慢。
- **对齐的效果**: 
    - 实现全链路独占式并发，每一个采集任务都能立即获得一个独占的 TDX 连接，最大化吞吐量。

---

## 3. 节点配置快照 (2026-01-17 已对齐)

目前 Server 41 作为主节点承担最高并发，Server 58 和 111 作为辅助分片节点。

| 节点 | 角色 | TDX_POOL_SIZE | 并发数 (Main/Retry) | 备注 |
|------|------|---------------|----------------------|------|
| **Server 41** | Shard 0 + 调度 | 50 | 50 / 50 | 高性能核心节点 |
| **Server 58** | Shard 1 | 10 | 10 / 10 | 边缘辅助节点 |
| **Server 111** | Shard 2 | 10 | 10 / 10 | 边缘辅助节点 |

### 3.1 环境变量对照表
- `TDX_POOL_SIZE`: 在 `mootdx-api` 容器中配置。
- `MOOTDX_CONCURRENCY`: 在 `gsd-worker` 容器中配置，用于 `sync_tick` 任务。
- `--concurrency`: 在 `tasks.yml` 的 `retry_tick` 命令参数中显式指定。

---

## 4. 采集算法：矩阵拼缝 (Matrix-Stitching Algorithm)

由于通达信 (TDX) 协议单次请求限制及游标不稳定，系统采用矩阵拼缝算法（V3）确保高频股票的数据完整性。

### 4.1 拼缝原理 (V3 Matrix)
`TickFetcher` 不再使用固定区间跳转，而是采用 **重叠分片 (Overlapping Slices)** 采集：
1. **分片采集**: 每次采集 800 条记录（offset=800），但步进仅为 600 条（step=600），确保每页之间有 200 条重叠。
2. **序列匹配 (Stitching)**: 利用 V2 版去重器的 **Occurrence-based Fingerprinting**（时间+价格+量+出现序号），在内存中将重叠的快照点精确对齐。
3. **全局排序**: 拉取完成后，对全天所有非重复成交笔进行全量升序排序，并重新分配全局唯一的 `num` 序号。

### 4.2 早停机制 (Early Stopping)
- **目标**: 捕获 `09:25`（集合竞价）数据。
- **逻辑**: 当任意一页分片中最早的时间戳 `earliest_time <= 09:25`，则立即终止拉取，进入排序拼缝阶段。
- **优势**: 完美解决了权重股（如 600036, 603993）由于成交密集导致的 API 游标跳跃/丢包问题。

---

## 5. 质量保证与自愈

### 5.1 三级审计
1. **Collector 校验**: 采集时确保命中 09:25。
2. **Post-Market Gate**: 盘后对比 ClickHouse 记录数与历史均值。
3. **分层修复**: 根据 Gate 发现的缺失程度（少量/大面积）触发自动补采。

### 5.2 状态追踪
所有股票的采集状态实时更新至 Redis `sync:status:tick` Hash 中，记录：
- `status`: processing/completed/failed/skipped
- `count`: 记录条数
- `time_range`: 数据的时间跨度 (如 `09:25-15:00`)

---

## 6. 运维指南

### 6.1 手动触发补采

该命令运行 `jobs.retry_tick` 脚本，其执行逻辑如下：
1. **自动扫描**: 扫描 Redis 中的 `sync:status:tick` 记录，筛选出状态为 `failed` 或数据开始时间晚于 `09:25`（疑似漏记）的股票。
2. **定向补采**: 仅针对筛选出的异常股票重新发起采集请求。
3. **适用场景**: 每日盘后采集完成后，用于自动质量自愈，确保 09:25 数据的覆盖率。

根据节点配置，运行以下命令：

- **Server 41 (Shard 0)**:
  ```bash
  docker run --rm gsd-worker jobs.retry_tick --concurrency 50
  ```

- **Server 58 (Shard 1)**:
  ```bash
  docker run --rm gsd-worker jobs.retry_tick --concurrency 10
  ```

- **Server 111 (Shard 2)**:
  ```bash
  docker run --rm gsd-worker jobs.retry_tick --concurrency 10
  ```

### 6.2 调整并发
如需提升速度，必须**成对修改**:
1. 修改 `docker-compose` 中的 `TDX_POOL_SIZE`。
2. 修改 `tasks.yml` 中的 `--concurrency` (针对 Retry) 和环境变量 `MOOTDX_CONCURRENCY` (针对 Main)。
3. 重启相关容器。

---

## 7. 运行场景描述

系统在不同时间段及应对不同需求时，呈现以下典型运行场景：

### 7.1 场景一：每日收盘全量同步 (Post-Market Full Sync)
- **时间**: 15:35 (交易日)
- **触发器**: `task-orchestrator` 的 `daily_tick_sync` 工作流。
- **运行逻辑**: 
    - 3 个节点并行启动。
    - 各节点根据 `shard_index` 仅拉取分配给自己的股票列表。
    - 采用最大限度并发（Server 41 并发 50, Server 58/111 并发 10）。
- **定时运行命令 (Orchestrator)**:
  `["jobs.sync_tick", "--scope", "all", "--shard-index", "{n}", "--shard-total", "3"]`
- **手动触发命令**:
  ```bash
  # 推荐方式 (自动继承网络与环境变量):
  docker-compose -f docker-compose.node-41.yml run --rm gsd-worker jobs.sync_tick --scope all --shard-index 0 --shard-total 3 --concurrency 50

  # 原生 Docker 方式 (必须指定网络模式):
  docker run --rm --network host gsd-worker jobs.sync_tick --scope all --shard-index 0 --shard-total 3 --concurrency 50
  ```
- **目标**: 在 60-90 分钟内完成 A 股全市场 5300+ 只股票的当日分笔同步。

### 7.2 场景二：自动化质量自愈 (Quality Self-Healing)
- **时间**: 19:18 (交易日)
- **触发器**: `task-orchestrator` 的 `post_market_gate` 任务。
- **运行逻辑**: 
    - 运行 `jobs.retry_tick`。
    - 系统自动对比 ClickHouse 与 Redis 状态，识别由于网络抖动或节点限流导致的失败及 09:25 数据缺失。
    - 仅对“故障股票”执行定向重采。
- **定时运行命令 (Orchestrator)**:
  `["jobs.retry_tick", "--concurrency", "{n}"]`
- **手动触发命令**:
  ```bash
  # 推荐方式:
  docker-compose -f docker-compose.node-41.yml run --rm gsd-worker jobs.retry_tick --concurrency 50

  # 原生 Docker 方式:
  docker run --rm --network host gsd-worker jobs.retry_tick --concurrency 50
  ```
- **目标**: 确保最终入库数据的 09:25 覆盖率达到 99% 以上。

### 7.3 场景三：历史数据修补/回测准备 (Historical Data Repair)
- **方式**: 手动触发
- **运行逻辑**: 
    - 运维人员指定历史日期。
    - 采集器切换至 `transactions` 接口获取历史分笔。
- **手动触发命令**:
  ```bash
  # 推荐方式 (自动继承所有配置):
  docker-compose -f docker-compose.node-41.yml run --rm gsd-worker jobs.sync_tick --date 20260115 --scope all --concurrency 50
  
  # 原生 Docker 方式 (需手动指定所有环境变量):
  docker run --rm --network host \
    -e CLICKHOUSE_HOST=127.0.0.1 \
    -e CLICKHOUSE_PORT=9000 \
    -e CLICKHOUSE_USER=admin \
    -e CLICKHOUSE_PASSWORD=admin123 \
    -e CLICKHOUSE_DB=stock_data \
    -e REDIS_HOST=127.0.0.1 \
    -e REDIS_PORT=6379 \
    -e REDIS_PASSWORD=redis123 \
    -e REDIS_CLUSTER=false \
    -e MOOTDX_API_URL=http://127.0.0.1:8003 \
    -e GSD_DB_HOST=127.0.0.1 \
    -e GSD_DB_PORT=36301 \
    -e GSD_DB_USER=root \
    -e GSD_DB_PASSWORD=alwaysup@888 \
    -e GSD_DB_NAME=alwaysup \
    gsd-worker jobs.sync_tick --date 20260115 --scope all --concurrency 50
  ```
- **目标**: 补全历史缺失数据，为回测提供高质量样本。


> **重要提示**: 原生 `docker run` 命令需要手动传递 14+ 个环境变量，极易出错。**强烈建议使用 `docker-compose run`**，它会自动从 YAML 配置中继承所有必要的环境变量和网络设置。

### 7.4 场景四：定向个股紧急补充 (On-demand Supplement)
- **方式**: API 或 手动触发
- **运行逻辑**: 
    - 忽略分片规则，直接在当前节点采集指定股票。
    - 绕过常规调度，最高优先级执行。
- **手动触发命令**:
  ```bash
  python -m jobs.supplement_stock --stock-codes 600519 --data-types tick
  ```
- **目标**: 满足特定策略对个股数据的紧急需求。

---

## 8. 数据验证

采集完成后，可通过 ClickHouse 查询验证数据完整性。

### 8.1 快速统计 (SQL)

```sql
-- 统计指定日期的总记录数和覆盖股票数
SELECT 
    count() AS total_rows,
    uniq(stock_code) AS stock_count
FROM stock_data.tick_data 
WHERE trade_date = '2026-01-15';
```

**预期结果参考**:
- **total_rows**: > 1000 万 (全市场分笔约为 1200-1500万，历史补采可能略少)
- **stock_count**: > 5000 (A股全市场股票数量)

### 8.2 命令行验证
在 Server 41 执行:
```bash
docker exec -i microservice-stock-clickhouse clickhouse-client -u admin --password admin123 -q "SELECT count(), uniq(stock_code) FROM stock_data.tick_data WHERE trade_date = '2026-01-15'"
```

---

### 9.1 审计原理 (V3)
- **多维比对**：从 ClickHouse 提取分笔统计值（笔数、总量、成交额、收盘价），并与 MySQL/ClickHouse 中的 K 线数据进行比对。
- **三级深度审计**：
    - **L1 (Existence)**: 检查股票是否完全缺失。
    - **L2 (Price)**: 检查分笔最后一条价格与 K 线收盘价是否偏差超过 0.01。
    - **L3 (Volume/Amount)**: 检查分笔累计成交量/额与 K 线偏差是否超过 2%。
- **时序对齐边界**: 审计对比量能时，代码自动过滤 `tick_time <= '15:00:00'`。

### 9.2 审计任务执行

- **推荐方式 (基于 Compose)**:
  ```bash
  docker-compose -f docker-compose.node-41.yml run --rm gsd-worker jobs.audit_tick_resilience --date 2026-01-30
  ```

- **原生 Docker 方式 (需手动注入关键环境)**:
  ```bash
  docker run --rm --network host \
    -e MYSQL_HOST=127.0.0.1 \
    -e MYSQL_PORT=36301 \
    -e MYSQL_USER=root \
    -e MYSQL_PASSWORD=alwaysup@888 \
    -e MYSQL_DATABASE=alwaysup \
    -e CLICKHOUSE_HOST=127.0.0.1 \
    -e CLICKHOUSE_PORT=9000 \
    -e CLICKHOUSE_USER=admin \
    -e CLICKHOUSE_PASSWORD=admin123 \
    -e CLICKHOUSE_DB=stock_data \
    -e REDIS_HOST=127.0.0.1 \
    -e REDIS_PORT=6379 \
    -e REDIS_PASSWORD=redis123 \
    -v $(pwd)/services/gsd-worker/src:/app/src \
    -v $(pwd)/libs/gsd-shared:/app/libs/gsd-shared:ro \
    -e PYTHONPATH=/app/src:/app/libs/gsd-shared \
    --entrypoint python gsd-worker:latest -m jobs.audit_tick_resilience --date 2026-01-30
  ```

### 9.3 审计输出
任务执行完成后会打印结构化 JSON (`GSD_OUTPUT_JSON`)，该 JSON 包含 `missing_list`（缺失及重影名单）和 `abnormal_list`（异常名单），可直接作为流水线中 `execute_repair` 步骤的输入，驱动系统实现闭环自愈。
