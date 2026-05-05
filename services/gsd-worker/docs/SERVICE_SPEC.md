# gsd-worker 服务规格说明

> **版本**: v1.0  
> **更新时间**: 2026-01-17  
> **服务类型**: 任务执行器 (无常驻端口)  
> **状态**: ✅ 生产环境

---

## 1. 服务概述

`gsd-worker` 是股票数据处理的任务执行器，负责 K 线同步、分笔数据采集、数据质量检测和修复等核心数据任务。采用"临时任务模式"，由 `task-orchestrator` 调度启动。

### 1.1 核心职责

| 职责 | 描述 |
|------|------|
| K 线数据同步 | MySQL → ClickHouse 增量/全量同步 |
| 分笔数据采集 | 通过 mootdx-api 获取历史分笔并存储 |
| 股票代码采集 | 每日更新股票列表并计算分片 |
| 数据质量门禁 | 盘前/盘后数据完整性检查 |
| 自动修复 | 缺失数据自动补采 |

### 1.2 技术栈

| 组件 | 技术 |
|------|------|
| 运行时 | Python 3.12+ |
| 数据库 | MySQL (源) + ClickHouse (目标) |
| 缓存 | Redis (锁/状态/分片元数据) |
| 数据源 | mootdx-api (HTTP) |
| 调度 | task-orchestrator (Docker 启动) |

---

## 2. 任务清单

### 2.1 任务索引

| 任务 ID | 入口文件 | 调度时间 | 优先级 | 描述 |
|---------|---------|---------|--------|------|
| `daily_stock_collection` | `jobs/daily_stock_collection.py` | 08:45 | P0 | 股票代码采集 + 分片计算 |
| `daily_kline_sync` | `jobs/sync_kline.py` | 17:30 | P0 | K 线每日同步 |
| `daily_tick_sync` | `jobs/sync_tick.py` | 15:35 | P1 | 分笔数据全量采集 |
| `pre_market_gate` | `jobs/pre_market_gate.py` | 09:15 | P0 | 盘前质量门禁 |
| `post_market_gate` | `jobs/post_market_gate.py` | 19:18 | P0 | 盘后审计门禁 |
| `quality_check` | `jobs/quality_check.py` | 手动 | P1 | 数据质量检测 |
| `retry_tick` | `jobs/retry_tick.py` | 自动 | P1 | 分笔失败重试 |
| `supplement_stock` | `jobs/supplement_stock.py` | API | P1 | 定向个股补采 |
| `weekly_audit` | `jobs/weekly_audit.py` | 周日 02:00 | P2 | 每周深度审计 |

---

## 3. 任务详细规格

### 3.1 daily_stock_collection (每日股票采集)

**入口**: `jobs/daily_stock_collection.py`  
**触发**: 每日 08:45 (交易日)

**功能**:
1. 从云端 API 拉取全市场股票列表
2. 过滤出有效 A 股代码 (排除 B 股、新股等)
3. 基于 Hash 计算 3 分片分配
4. 将分片结果存储到 Redis

**输出 Redis Key**:
| Key | 说明 |
|-----|------|
| `stock:codes:shard:0` | Shard 0 股票列表 (Server 41) |
| `stock:codes:shard:1` | Shard 1 股票列表 (Server 58) |
| `stock:codes:shard:2` | Shard 2 股票列表 (Server 111) |
| `stock:codes:metadata` | 分片元数据 (时间戳、总数) |

**命令行**:
```bash
python -m jobs.daily_stock_collection
```

---

### 3.2 sync_kline (K 线同步)

**入口**: `jobs/sync_kline.py`  
**触发**: 每日 17:30 (交易日)

**同步模式**:

| 模式 | 参数 | 描述 |
|------|------|------|
| `adaptive` | `--mode adaptive` | 自适应智能增量同步 (默认) |
| `full` | `--mode full` | 全量同步 |
| `incremental` | `--mode incremental` | 增量同步 |

**核心逻辑** (`KLineSyncService.sync_smart_incremental`):
1. 查询 ClickHouse 最新日期及记录数
2. 与 MySQL 云端数据对比
3. 如有差异，删除该日期数据并重同步
4. 同步所有新增日期的数据

**数据校验**:
- L1: 基础合法性 (字段非空、类型正确)
- L2: 历史一致性 (价格跳变 <30%)
- L5: 跨字段关联 (OHLC 范围、成交额验证)
- L7: 批次完整性 (去重)

**命令行**:
```bash
# 智能增量同步
python -m jobs.sync_kline --mode adaptive

# 分片同步 (4 分片中的第 1 个)
python -m jobs.sync_kline --shard 0 --total 4
```

---

### 3.3 sync_tick (分笔数据采集)

**入口**: `jobs/sync_tick.py`  
**触发**: 每日 15:35 (交易日)

**参数**:

| 参数 | 说明 |
|------|------|
| `--scope` | `all` 全量 / `hs300` 沪深300 |
| `--shard-index` | 当前分片索引 (0/1/2) |
| `--shard-total` | 总分片数 (3) |
| `--date` | 指定日期 (YYYYMMDD) |

**采集流程**:
1. 从 Redis 获取分片股票列表
2. 调用 mootdx-api 获取分笔数据
3. 使用"搜索矩阵"策略确保数据完整性
4. 写入 ClickHouse `tick_data_intraday` 表
5. 失败股票记录到 `failed_stocks` 队列

**分布式架构**:
```
Server 41: --shard-index 0 --shard-total 3
Server 58: --shard-index 1 --shard-total 3
Server 111: --shard-index 2 --shard-total 3
```

**命令行**:
```bash
# Shard 0 全量采集
python -m jobs.sync_tick --scope all --shard-index 0 --shard-total 3

# 指定日期采集
python -m jobs.sync_tick --scope all --date 20260115
```

---

### 3.4 pre_market_gate (盘前质量门禁)

**入口**: `jobs/pre_market_gate.py`  
**触发**: 每日 09:15 (交易日)

**检查项**:
| 检查项 | 阈值 | 说明 |
|--------|------|------|
| K 线覆盖率 | ≥98% | ClickHouse 相对 MySQL 的覆盖率 |
| 分笔覆盖率 | ≥95% | 昨日分笔数据完整性 |
| 股票列表更新 | 当日 | Redis 分片元数据是否最新 |

**失败处理**:
- 记录告警到 Redis
- 触发自动补采流程 (如配置)

---

### 3.5 post_market_gate (盘后审计门禁)

**入口**: `jobs/post_market_gate.py`  
**触发**: 每日 19:18 (交易日)

**审计流程**:
1. **K 线审计**: 对比 ClickHouse 与 MySQL 记录数
2. **分笔审计**: 检查当日分笔采集完整性
3. **分层修复**: 根据缺失程度选择修复策略
4. **报告生成**: 输出审计结果到日志/Redis

**修复策略**:
| 缺失程度 | 策略 |
|---------|------|
| 少量 (<5%) | 逐只补采 |
| 中等 (5-20%) | 批量补采 |
| 大量 (>20%) | 触发全量重采 |

**命令行**:
```bash
python -m jobs.post_market_gate
```

---

### 3.6 supplement_stock (定向个股补采)

**入口**: `jobs/supplement_stock.py`  
**触发**: API/Gate-3

**参数** (JSON):
```json
{
  "stocks": ["000001", "600519"],
  "data_types": ["tick", "kline", "financial"],
  "date": "20260115"
}
```

**支持的数据类型**:
| 类型 | 收集器 | 说明 |
|------|--------|------|
| `tick` | TickCollector | 分笔数据 |
| `kline` | KlineCollector | K 线数据 |
| `financial` | FinancialCollector | 财务数据 |
| `shareholder` | ShareholderCollector | 股东数据 |

---

## 4. 核心服务组件

### 4.1 KLineSyncService

**文件**: `src/core/sync_service.py`

K 线同步核心服务，负责 MySQL → ClickHouse 的数据迁移。

**关键方法**:

| 方法 | 说明 |
|------|------|
| `initialize()` | 初始化连接池 |
| `close()` | 关闭连接池 |
| `sync_smart_incremental()` | 智能增量同步 (自愈版) |
| `sync_full()` | 全量同步 |
| `sync_by_stock_codes()` | 按股票代码同步 |
| `verify_consistency()` | 验证数据一致性 |

---

### 4.2 TickSyncService

**文件**: `src/core/tick_sync_service.py`

分笔数据采集服务。

**关键方法**:

| 方法 | 说明 |
|------|------|
| `sync_stock_tick()` | 单只股票分笔采集 |
| `sync_batch()` | 批量采集 |
| `get_failed_stocks()` | 获取失败列表 |

---

### 4.3 PostMarketGateService

**文件**: `src/core/post_market_gate_service.py`

盘后审计门禁服务。

**关键方法**:

| 方法 | 说明 |
|------|------|
| `run_gate()` | 执行完整审计流程 |
| `_check_kline_coverage()` | K 线覆盖率检查 |
| `_check_tick_coverage()` | 分笔覆盖率检查 |
| `_process_tiered_repair()` | 分层修复处理 |

---

### 4.4 SupplementEngine

**文件**: `src/core/supplement_engine.py`

定向数据补充引擎。

**收集器注册表**:
```python
collectors = {
    "tick": TickCollector,
    "kline": KlineCollector,
    "financial": FinancialCollector,
    "shareholder": ShareholderCollector,
}
```

---

## 5. 配置

### 5.1 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MYSQL_HOST` | - | MySQL 地址 |
| `MYSQL_PORT` | 3306 | MySQL 端口 |
| `MYSQL_USER` | - | MySQL 用户名 |
| `MYSQL_PASSWORD` | - | MySQL 密码 |
| `CLICKHOUSE_HOST` | - | ClickHouse 地址 |
| `CLICKHOUSE_PORT` | 9000 | ClickHouse 端口 |
| `REDIS_HOST` | 127.0.0.1 | Redis 地址 |
| `REDIS_PORT` | 6379 | Redis 端口 |
| `REDIS_PASSWORD` | - | Redis 密码 |
| `MOOTDX_API_URL` | http://mootdx-api:8003 | mootdx-api 地址 |
| `KLINE_THRESHOLD` | 98 | K 线覆盖率阈值 |
| `TICK_THRESHOLD` | 95 | 分笔覆盖率阈值 |

### 5.2 配置文件

**文件**: `config/settings.yml`

```yaml
sync:
  batch_size: 10000
  max_retries: 3
  retry_delay: 5

tick:
  concurrency: 5
  timeout: 30
  
quality:
  kline_threshold: 98
  tick_threshold: 95
```

---

## 6. 数据表结构

### 6.1 ClickHouse 表

| 表名 | 说明 |
|------|------|
| `stock_kline_daily` | 日 K 线数据 (分布式) |
| `tick_data` | 分笔历史数据 (分布式) |
| `tick_data_intraday` | 分笔当日数据 (分布式) |
| `stock_adjust_factor` | 复权因子 |

### 6.2 Redis Key

| Key | 类型 | 说明 |
|-----|------|------|
| `sync:status:kline` | Hash | K 线同步状态 |
| `sync:status:tick` | Hash | 分笔同步状态 |
| `stock:codes:shard:*` | Set | 分片股票列表 |
| `stock:failed:tick` | List | 分笔失败队列 |

---

## 7. 部署

### 7.1 Docker 运行

```bash
# K 线同步
docker run --rm --network host gsd-worker python -m jobs.sync_kline

# 分笔同步 (Shard 0)
docker run --rm --network host gsd-worker python -m jobs.sync_tick --scope all --shard-index 0 --shard-total 3

# 质量检测
docker run --rm --network host gsd-worker python -m jobs.quality_check
```

### 7.2 本地开发

```bash
cd services/gsd-worker
pip install -e ../../libs/gsd-shared
pip install -r requirements.txt

python -m jobs.sync_kline --mode adaptive
```

---

## 8. 依赖服务

| 服务 | 用途 | 必需 |
|------|------|------|
| MySQL | 源数据 (K 线) | ✅ |
| ClickHouse | 目标存储 | ✅ |
| Redis | 锁/状态/分片 | ✅ |
| mootdx-api | 分笔数据源 | ✅ (分笔任务) |

---

## 9. 相关文档

| 文档 | 路径 |
|------|------|
| 采集策略与并发指南 | `TICK_ACQUISITION_STRATEGY_AND_CONCURRENCY.md` |
| 每日分笔同步场景 | `docs/SCENARIO_DAILY_TICK_SYNC.md` |
| 指定日期分笔场景 | `docs/SCENARIO_SPECIFIED_DATE_TICK.md` |
| 分笔服务重构说明 | `docs/REFACTORING_TICK_SYNC_SERVICE.md` |
| 分布式架构 | `../../docs/architecture/tick_data_sharding_implementation.md` |
