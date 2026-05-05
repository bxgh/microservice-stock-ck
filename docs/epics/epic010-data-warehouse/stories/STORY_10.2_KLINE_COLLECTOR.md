# Story 10.2: 日K线采集任务

## Story 信息

| 字段 | 值 |
|------|-----|
| **Story ID** | 10.2 |
| **所属 Epic** | EPIC-010 本地数据仓库 |
| **优先级** | P0 |
| **预估工时** | 3 天 |
| **前置依赖** | Story 10.0, 10.1 |

---

## 目标

实现从 Baostock 采集 A 股日K线数据，双写到 ClickHouse (本地) 和腾讯云 MySQL (备份)。

---

## 验收标准

1. ✅ 每日 18:00 自动执行采集任务
2. ✅ 采集全市场 ~5000 只股票日K线
3. ✅ 数据写入 ClickHouse `kline_daily` 表
4. ✅ 数据同步到腾讯云 MySQL
5. ✅ 支持增量更新 (只采集当日数据)
6. ✅ 支持历史补录 (指定日期范围)

---

## 任务分解

### Task 1: Baostock 采集器

```python
# src/collectors/baostock.py
import baostock as bs

class BaostockCollector:
    async def collect_daily_kline(
        self, 
        codes: list[str], 
        start_date: str, 
        end_date: str
    ) -> list[dict]:
        """采集日K线数据"""
        pass
    
    async def get_stock_list(self) -> list[str]:
        """获取全市场股票列表"""
        pass
```

### Task 2: ClickHouse 写入器

```python
# src/writers/clickhouse.py
class ClickHouseWriter:
    async def write_kline(self, data: list[dict]) -> int:
        """批量写入K线数据"""
        pass
```

### Task 3: MySQL 写入器

```python
# src/writers/mysql_cloud.py
class MySQLCloudWriter:
    async def write_kline(self, data: list[dict]) -> int:
        """写入腾讯云 MySQL"""
        pass
```

### Task 4: 双写协调器

```python
# src/writers/dual_writer.py
class DualWriter:
    def __init__(self, clickhouse: ClickHouseWriter, mysql: MySQLCloudWriter):
        self.clickhouse = clickhouse
        self.mysql = mysql
    
    async def write(self, data: list[dict]) -> tuple[int, int]:
        """并行双写，返回两边写入数量"""
        pass
```

### Task 5: 定时任务配置

```python
# src/scheduler/jobs.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

def setup_jobs(scheduler: AsyncIOScheduler):
    # 每日 18:00 执行
    scheduler.add_job(
        daily_kline_job,
        'cron',
        hour=18,
        minute=0,
        timezone='Asia/Shanghai'
    )
```

---

## 数据源说明

- **数据源**: Baostock `bs.query_history_k_data_plus()`
- **字段映射**:

| Baostock 字段 | 目标字段 |
|--------------|---------|
| code | stock_code |
| date | trade_date |
| open | open |
| high | high |
| low | low |
| close | close |
| volume | volume |
| amount | amount |
| turn | turnover_rate |
| adjustflag | adj_factor |

---

*创建日期: 2025-12-23*
