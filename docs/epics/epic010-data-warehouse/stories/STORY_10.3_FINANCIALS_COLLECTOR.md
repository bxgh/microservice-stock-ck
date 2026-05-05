# Story 10.3: 财务数据采集任务

## Story 信息

| 字段 | 值 |
|------|-----|
| **Story ID** | 10.3 |
| **所属 Epic** | EPIC-010 本地数据仓库 |
| **优先级** | P0 |
| **预估工时** | 3 天 |
| **前置依赖** | Story 10.0, 10.1 |

---

## 目标

实现从 AkShare 采集 A 股财务报表数据，写入 ClickHouse 和腾讯云 MySQL。

---

## 验收标准

1. ✅ 季度财报发布后 3 天内自动采集
2. ✅ 采集字段: 营收、净利润、EPS、ROE、毛利率等
3. ✅ 数据写入 ClickHouse `financials` 表
4. ✅ 数据同步到腾讯云 MySQL
5. ✅ 支持历史补录 (指定报告期)

---

## 任务分解

### Task 1: AkShare 财务采集器

```python
# src/collectors/akshare.py
import akshare as ak

class AkShareCollector:
    async def collect_financials(
        self, 
        codes: list[str],
        report_date: str  # e.g., "20250930"
    ) -> list[dict]:
        """采集财务报表数据"""
        # ak.stock_financial_report_sina()
        pass
```

### Task 2: 财报发布日历

```python
# src/scheduler/calendar.py
FINANCIAL_REPORT_DATES = {
    "Q1": ("04-01", "04-30"),  # 一季报披露期
    "Q2": ("07-01", "08-31"),  # 中报披露期
    "Q3": ("10-01", "10-31"),  # 三季报披露期
    "ANNUAL": ("01-01", "04-30"),  # 年报披露期
}
```

### Task 3: 定时任务

```python
# 财报季自动扫描
scheduler.add_job(
    financial_scan_job,
    'cron',
    day='1,15',  # 每月 1 号和 15 号扫描
    hour=20,
    timezone='Asia/Shanghai'
)
```

---

## 数据源说明

- **数据源**: AkShare `ak.stock_financial_analysis_indicator()`
- **字段映射**:

| AkShare 字段 | 目标字段 |
|-------------|---------|
| 股票代码 | stock_code |
| 报告期 | report_date |
| 营业收入 | revenue |
| 净利润 | net_profit |
| 每股收益 | eps |
| 净资产收益率 | roe |
| 毛利率 | gross_margin |
| 经营现金流 | operating_cash_flow |

---

*创建日期: 2025-12-23*
