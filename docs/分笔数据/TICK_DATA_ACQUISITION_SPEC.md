# 分笔数据采集系统规格说明书 (Tick Data Acquisition Spec)

> **版本**: v1.2  
> **更新时间**: 2026-02-01  
> **状态**: ✅ 生产环境 (已集成矩阵拼缝算法)

---

## 1. 系统概述

本文档定义了 A 股分笔数据采集系统的三大核心场景：**盘中实时采集**、**盘后补采当天**、**盘后补采历史**。

### 1.1 架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                         分笔数据采集系统                           │
├──────────────┬──────────────────┬────────────────────────────────┤
│  场景一       │     场景二        │         场景三                  │
│  盘中实时采集  │  盘后补采当天      │      盘后补采历史               │
├──────────────┼──────────────────┼────────────────────────────────┤
│ get-stockdata│   gsd-worker     │        gsd-worker              │
│ (常驻服务)    │   (定时任务)      │        (手动/定时任务)          │
└──────────────┴──────────────────┴────────────────────────────────┘
```

### 1.2 数据源与存储

| 组件 | 技术 | 用途 |
|------|------|------|
| **数据源** | mootdx-api (HTTP) | 通达信分笔数据网关 |
| **存储** | ClickHouse | 本地表 + 分布式表 |
| **缓存** | Redis | 股票池分片 / 状态追踪 |
| **调度** | task-orchestrator | 任务触发与管理 |

---

## 2. 场景一：盘中实时采集

### 2.1 概述

| 属性 | 值 |
|------|-----|
| **服务** | `get-stockdata/intraday-tick-collector` |
| **运行模式** | 常驻容器 (09:25-15:00 自动运行) |
| **采集频率** | 快照 3秒/轮，分笔 5秒/轮 |
| **覆盖范围** | 全市场 ~5,800 只 A 股 |

### 2.2 代码位置

| 文件 | 职责 |
|------|------|
| `services/get-stockdata/src/core/collector/intraday_tick_collector.py` | 主编排器 |
| `services/get-stockdata/src/core/collector/components/writer.py` | ClickHouse 写入 |
| `services/get-stockdata/src/core/collector/components/snapshot_worker.py` | 快照采集 Worker |
| `services/get-stockdata/src/core/collector/components/tick_worker.py` | 分笔采集 Worker |

### 2.3 分布式架构

```
┌─────────────────────────────────────────────────────┐
│              Redis (Node 41 主节点)                  │
│  metadata:stock_codes:shard:0 → Shard 0 股票列表     │
│  metadata:stock_codes:shard:1 → Shard 1 股票列表     │
│  metadata:stock_codes:shard:2 → Shard 2 股票列表     │
└───────────────────────┬─────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Node 41   │ │   Node 58   │ │   Node 111  │
│   Shard 0   │ │   Shard 1   │ │   Shard 2   │
│  ~1,942只   │ │  ~1,925只   │ │  ~1,934只   │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       └───────────────┴───────────────┘
                       ▼
           ClickHouse (分布式表汇总)
```

### 2.4 数据流

```
1. 启动时: StockUniverseService → Redis → 获取分片股票池
2. 采集中: mootdx-api → SnapshotWorker/TickWorker → 指纹去重
3. 写入: ClickHouseWriter → snapshot_data_local / tick_data_intraday_local
4. 终止: 15:00 后自动停止或收到 SIGTERM
```

### 2.5 关键配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `SHARD_INDEX` | 0 | 当前分片索引 (0/1/2) |
| `SHARD_TOTAL` | 3 | 总分片数 |
| `SNAPSHOT_INTERVAL_SECONDS` | 3.0 | 快照采集间隔 |
| `POLL_INTERVAL_SECONDS` | 5.0 | 分笔轮询间隔 |
| `MOOTDX_API_URL` | http://127.0.0.1:8003 | mootdx-api 地址 |

### 2.6 文档索引

| 文档 | 路径 |
|------|------|
| 架构设计 | `docs/分笔数据/盘中全市场分片采集/01_ARCH_DESIGN.md` |
| 部署指南 | `docs/分笔数据/盘中全市场分片采集/02_DEPLOYMENT_GUIDE.md` |
| 故障排除 | `docs/分笔数据/盘中全市场分片采集/07_TROUBLESHOOTING.md` |
| 数据校验 | `docs/分笔数据/盘中全市场分片采集/08_INTRADAY_VALIDATION.md` |

---

## 3. 场景二：盘后补采当天

### 3.1 概述

| 属性 | 值 |
|------|-----|
| **服务** | `gsd-worker` (临时任务) |
| **触发时间** | 15:35 (daily_tick_sync) / 19:18 (post_market_gate) |
| **目标** | 补全当天盘中采集遗漏的分笔数据 |

### 3.2 代码位置

| 文件 | 职责 |
|------|------|
| `services/gsd-worker/src/jobs/sync_tick.py` | 分笔同步入口 |
| `services/gsd-worker/src/jobs/audit_tick_resilience.py` | 盘后精准审计 |
| `services/gsd-worker/src/core/tick_sync_service.py` | 分笔同步核心服务 |

### 3.3 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                    盘后精准审计流程 (V4.0)                     │
├─────────────────────────────────────────────────────────────┤
│  Audit Phase: audit_tick_resilience                         │
│         ├─ 确定对账基准: 快照 (≥11:30/15:00) -> 降级 K线       │
│         ├─ 精准对账标准: 价格误差 ≤ 0.1, 成交量误差 ≤ 0.5%   │
│         ├─ 识别缺失 & 质量异常股票                            │
│         └─ 生成自愈指令 (AI_AUDIT / FAILOVER)                 │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 关键方法

| `main()` | sync_tick.py | 分笔同步主入口 |
| `execute_validation()` | audit_tick_resilience.py | 执行精准审计对账 |

### 3.5 命令行接口

```bash
# 15:35 分笔全量同步 (Shard 0)
docker exec gsd-worker python -m jobs.sync_tick --scope all --shard-index 0 --shard-total 3

# 19:18 盘后审计门禁
docker exec gsd-worker python -m jobs.post_market_gate

# 手动触发盘中校验 (午休时段)
docker exec gsd-worker python -m jobs.intraday_tick_validation --session noon

# 手动触发盘中校验 (盘后时段)
docker exec gsd-worker python -m jobs.intraday_tick_validation --session close
```

### 3.6 文档索引

| 文档 | 路径 |
|------|------|
| 服务规格 | `services/gsd-worker/docs/SERVICE_SPEC.md` |
| 每日分笔场景 | `services/gsd-worker/docs/SCENARIO_DAILY_TICK_SYNC.md` |
| 采集策略 | `services/gsd-worker/docs/TICK_ACQUISITION_STRATEGY_AND_CONCURRENCY.md` |
| 精准审计设计 | `docs/分笔数据/TICK_DATA_PRECISE_AUDIT_DESIGN.md` |

---

## 4. 场景三：盘后补采历史

### 4.1 概述

| 属性 | 值 |
|------|-----|
| **服务** | `gsd-worker` (手动/定时任务) |
| **触发方式** | 手动 / 周审计自动触发 |
| **目标** | 补采历史缺失的分笔数据 |

### 4.2 代码位置

| 文件 | 职责 |
|------|------|
| `services/gsd-worker/src/jobs/retry_tick.py` | 自动重试脚本 |
| `services/gsd-worker/src/jobs/supplement_stock.py` | 定向个股补采 |
| `services/gsd-worker/src/core/tick_sync_service_rigorous.py` | 严谨完整性策略 |
| `services/gsd-worker/src/core/data_repair_service.py` | 数据修复服务 |

### 4.3 补采策略

#### 4.3.1 严谨完整性策略 (Rigorous Integrity-First)

```python
async def fetch_tick_data_rigorous(stock_code, trade_date):
    """
    1. [Baseline Fetch]: 标准顺序回溯，获取大部分数据
    2. [Gap Analysis]: 分析数据覆盖范围
    3. [Targeted Probe]: 如果缺失早盘 (min > 09:25)，启动智能矩阵搜索
    4. [Consensus]: 合并所有数据，去重排序
    """
```

#### 4.3.2 自动补采逻辑 (retry_tick.py)

```python
# 扫描 Redis 中的采集状态
# 识别需要重试的股票:
#   1. 状态标记为 "failed"
#   2. 数据开始时间晚于 09:25 (缺失早盘)
# 执行补采
```

### 4.4 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                    盘后补采历史流程                           │
├─────────────────────────────────────────────────────────────┤
│  方式一: 自动重试 (retry_tick)                                │
│         ├─ 读取 Redis tick_sync:status:{date}               │
│         ├─ 筛选 failed 或缺失早盘的股票                        │
│         └─ 调用 sync_stocks() 重新采集                        │
├─────────────────────────────────────────────────────────────┤
│  方式二: 定向补采 (supplement_stock)                          │
│         ├─ 接收 stocks + date 参数                           │
│         ├─ 调用 TickCollector 采集指定股票                    │
│         └─ 写入 ClickHouse                                   │
├─────────────────────────────────────────────────────────────┤
│  方式三: 周审计触发 (weekly_audit)                            │
│         ├─ 扫描过去 7 天数据完整性                             │
│         ├─ 识别缺失日期和股票                                  │
│         └─ 批量触发补采任务                                    │
└─────────────────────────────────────────────────────────────┘
```

### 4.5 命令行接口

```bash
# 自动补采 (扫描当天失败股票)
docker exec gsd-worker python -m jobs.retry_tick

# 指定日期补采
docker exec gsd-worker python -m jobs.retry_tick --date 20260120

# 定向个股补采 (通过 API 触发)
# POST /api/tasks/supplement_stock
# {"stocks": ["000001", "600519"], "data_types": ["tick"], "date": "20260115"}

# 历史日期同步
docker exec gsd-worker python -m jobs.sync_tick --scope all --date 20260110
```

### 4.6 文档索引

| 文档 | 路径 |
|------|------|
| 服务规格 | `services/gsd-worker/docs/SERVICE_SPEC.md` |
| 历史分笔场景 | `services/gsd-worker/docs/SCENARIO_SPECIFIED_DATE_TICK.md` |
| 重构说明 | `services/gsd-worker/docs/REFACTORING_TICK_SYNC_SERVICE.md` |

---

## 5. 数据表结构

### 5.1 盘中实时表 (get-stockdata 写入)

```sql
-- ClickHouse: snapshot_data_local
CREATE TABLE snapshot_data_local (
    snapshot_time DateTime64(3),
    trade_date Date,
    stock_code String,
    stock_name String,
    market String,
    current_price Decimal(10,3),
    -- ... 五档盘口 ...
    total_volume UInt64,
    total_amount Decimal(18,2)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, snapshot_time);

-- ClickHouse: tick_data_intraday_local
CREATE TABLE tick_data_intraday_local (
    stock_code String,
    trade_date Date,
    tick_time String,
    price Decimal(10,3),
    volume UInt32,
    amount Decimal(18,2),
    direction Int8
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, stock_code, tick_time);
```

### 5.2 盘后历史表 (gsd-worker 写入)

```sql
-- ClickHouse: tick_data (分布式表)
-- 与 tick_data_intraday_local 结构相同，通过 Distributed 引擎汇总
```

---

## 6. 调度配置

### 6.1 task-orchestrator 任务清单

| 任务 ID | 触发时间 | 服务 | 场景 |
|---------|---------|------|------|
| `intraday_tick_collector` | 09:20 启动 | get-stockdata | 场景一 |
| `calculate_data_quality`  | 对应工作流 | gsd-worker | 场景二 |
| `stock_data_supplement`   | 对应工作流 | gsd-worker | 场景二 |
| `weekly_audit` | 周日 02:00 | gsd-worker | 场景三 |

---

## 7. 监控与告警

### 7.1 Redis 状态键

| Key | 类型 | 说明 |
|-----|------|------|
| `tick_sync:status:{date}` | Hash | 每只股票采集状态 |
| `metadata:stock_codes:shard:{i}` | Set | 分片股票列表 |
| `sync:failed:tick` | List | 采集失败队列 |

### 7.2 覆盖率阈值

| 指标 | 阈值 | 处理 |
|------|------|------|
| 分笔覆盖率 | ≥95% | 通过 |
| 分笔覆盖率 | 90-95% | 告警 + 定向补采 |
| 分笔覆盖率 | <90% | 告警 + 全量重采 |

---

## 8. 相关文档汇总

| 分类 | 文档 | 路径 |
|------|------|------|
| **盘中采集** | 总览 | `docs/分笔数据/盘中全市场分片采集/README.md` |
| | 架构设计 | `docs/分笔数据/盘中全市场分片采集/01_ARCH_DESIGN.md` |
| | 部署指南 | `docs/分笔数据/盘中全市场分片采集/02_DEPLOYMENT_GUIDE.md` |
| | 数据校验 | `docs/分笔数据/盘中全市场分片采集/08_INTRADAY_VALIDATION.md` |
| **分笔服务** | 服务规格 | `services/gsd-worker/docs/SERVICE_SPEC.md` |
| | 采集策略 | `services/gsd-worker/docs/TICK_ACQUISITION_STRATEGY_AND_CONCURRENCY.md` |
| **架构** | 分片实现 | `docs/architecture/tick_data_sharding_implementation.md` |
| | HS300采集器 | `docs/architecture/data_acquisition/HS300_INTRADAY_TICK_COLLECTOR.md` |
| **分析** | 分笔应用 | `docs/分笔数据/分笔数据分析应用指南.md` |
| | 量化框架 | `docs/分笔数据/分笔数据量化思维深度分析框架.md` |
