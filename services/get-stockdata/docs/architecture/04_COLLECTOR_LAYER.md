# 实时采集器层 (Collector Layer)

**实现路径**: `src/core/collector/` (主动采集模式)

## 1. 运行模式：主动采集 (Active Mode)

与被动响应不同，本层是后台常驻任务。它负责全市场分笔和快照数据的实时抓取、去重与持久化。

### 核心组件
- **IntradayTickCollector**: 总控任务，负责生命周期和信号处理。
- **TickWorker**: 负责分笔数据 (Transaction-by-transaction) 的采集逻辑。
- **SnapshotWorker**: 负责五档快照 (L1 Depth) 的批量采集。
- **Writer**: 负责内存缓冲与 ClickHouse 写入。

---

## 2. 采集流水线 (Data Pipeline)

采集器遵循以下严格的流程确保数据质量：

1.  **分片过滤**: 通过 `gsd_shared.stock_universe` 获取当前节点负责的股票池。
2.  **异步拉取**: 使用 `TickFetcher` 进行并行抓取。
3.  **智能去重**: 调用 `gsd_shared.tick.TickDeduplicator` 基于指纹 (Time, Price, Vol) 判定。
4.  **缓冲持久化**:
    - **Buffer**: 累积到 `FLUSH_THRESHOLD`。
    - **Flash**: 批量写入 ClickHouse 盘中表 `tick_data_intraday_local`。

---

## 3. 分片与水平扩展 (Sharding)

为了支持 5000+ 股票的秒级更新，系统实现了物理分片：

- **配置项**: `SHARD_INDEX` 和 `SHARD_TOTAL`。
- **动态发现**: 逻辑解耦，只需增加计算节点（如 Node 58, 111）并调整环境变量，系统自动重新分配采集压力。

---

## 4. 容错与自愈

- **交易感应**: 自动轮询 `CalendarService`，非交易时段自动进入低功耗休眠（1分钟/次检测）。
- **进程守卫**: 运行在 Docker 容器中，配置有健康检查 `healthcheck`，确保挂死后自动重启。
- **异步解耦**: 采用 `asyncio.gather` 并发轮询，单只股票获取失败不会导致主任务阻塞。
