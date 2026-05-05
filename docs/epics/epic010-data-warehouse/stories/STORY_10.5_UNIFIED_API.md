# Story 10.5: 统一数据访问 API

## Story 信息

| 字段 | 值 |
|------|-----|
| **Story ID** | 10.5 |
| **所属 Epic** | EPIC-010 本地数据仓库 |
| **优先级** | P1 |
| **预估工时** | 4 天 |
| **前置依赖** | Story 10.4 |

---

## 目标

实现 K线、财务、估值、因子等数据的查询 API。

---

## 验收标准

1. ✅ K线查询接口可用
2. ✅ 财务数据查询接口可用
3. ✅ 估值数据查询接口可用
4. ✅ 因子数据查询接口可用
5. ✅ 响应时间 < 100ms (单股票查询)

---

## API 清单

### 1. K线查询

```
GET /api/v1/data/kline/daily
Query:
  - codes: string[]
  - start: date
  - end: date
```

### 2. 财务数据查询

```
GET /api/v1/data/financials/{code}
Query:
  - periods: int = 8
```

### 3. 估值数据查询

```
GET /api/v1/data/valuation/{code}/history
Query:
  - years: int = 5
```

### 4. 因子数据查询

```
GET /api/v1/data/factors/{factor_id}
Query:
  - codes: string[]
  - date: date
```

---

*创建日期: 2025-12-23*
