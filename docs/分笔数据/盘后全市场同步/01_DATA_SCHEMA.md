# 01 数据结构与存储规格

## 1. 数据库定义
所有分笔相关数据存储在 ClickHouse 的 `stock_data` 数据库中。

## 2. 核心表结构

### 2.1 原始分笔表 (tick_data_local)
该表存储每一笔成交明细。
*   **引擎**: `ReplicatedReplacingMergeTree`
*   **排序键**: `(ts_code, trade_date, tick_time, price, volume)`
*   **分区**: `toYYYYMM(trade_date)` (按月分区)
*   **TTL**: `trade_date + INTERVAL 365 DAY` (保留一年)

| 字段 | 类型 | 说明 |
|---|---|---|
| `ts_code` | String | 归一化代码 (如 600519.SH) |
| `trade_date` | Date | 交易日期 |
| `tick_time` | String | 成交时间 (HH:MM:SS) |
| `price` | Decimal(10, 3) | 成交价 |
| `volume` | UInt32 | 成交量 (股) |
| `amount` | Decimal(18, 2) | 成交额 (元) |
| `direction` | UInt8 | 0=买, 1=卖, 2=中性 |
| `num` | UInt32 | 成交笔数 |

### 2.2 每日统计物化视图 (tick_daily_stats)
通过物化视图预聚合，支撑异动分析。
*   **引擎**: `SummingMergeTree`
*   **聚合维度**: `(ts_code, trade_date)`

| 字段 | 计算逻辑 | 用途 |
|---|---|---|
| `tick_count` | `count()` | 活跃度分析 |
| `buy_volume` | `sumIf(volume, direction=0)` | 主力流入计算 |
| `sell_volume` | `sumIf(volume, direction=1)` | 主力流出计算 |
| `low_price` | `min(price)` | 价格区间校验 |
| `high_price` | `max(price)` | 价格区间校验 |
| `buy_amount` | `sumIf(amount, direction=0)` | 主力流入金额 |
| `sell_amount` | `sumIf(amount, direction=1)` | 主力流出金额 |

## 3. 审计基准表 (MySQL: stock_kline_daily)
Gate-3 审计使用 MySQL 中的 `stock_kline_daily` 作为基准。
*   **关键约定**: 该表中的 `volume` 字段单位为 **股 (Shares)**，计算审计差异时不需要进行 `* 100` 换算。

| 字段 | 类型 | 说明 |
|---|---|---|
| `ts_code` | varchar | 股票代码 (如 600519.SH) |
| `trade_date` | date | 交易日期 |
| `volume` | bigint | **成交量 (股)** |
| `amount` | decimal | 成交额 (元) |

## 3. 分布式视图
在集群环境下，通过 `Distributed` 引擎创建 `tick_data` 表，映射至各节点的 `tick_data_local`。

## 4. 接入规范
- **写入端**：仅允许由 `gsd-worker` 容器执行 `jobs.sync_tick` 写入，确保 `created_at` 顺序性。
- **查询端**：异动评分逻辑应优先查询 `tick_daily_stats` 聚合表，仅在需要分时波形分析时回溯 `tick_data`。
