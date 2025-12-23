# Story 10.6: 因子存储集成

## Story 信息

| 字段 | 值 |
|------|-----|
| **Story ID** | 10.6 |
| **所属 Epic** | EPIC-010 本地数据仓库 |
| **优先级** | P1 |
| **预估工时** | 3 天 |
| **前置依赖** | Story 10.5 |

---

## 目标

将 `quant-strategy` 计算的因子值持久化到 ClickHouse，支持因子回溯和回测。

---

## 验收标准

1. ✅ 因子写入 API 可用
2. ✅ 因子查询 API 可用
3. ✅ `quant-strategy` 可调用写入因子
4. ✅ 数据保留 1 年自动清理

---

## API 清单

### 1. 写入因子值

```
POST /api/v1/data/factors/write
Body:
{
  "factor_id": "roe_rank",
  "date": "2025-12-23",
  "values": {
    "600519": 85.5,
    "000001": 72.3
  }
}
```

### 2. 批量查询因子

```
POST /api/v1/data/factors/batch
Body:
{
  "factor_ids": ["roe_rank", "pe_percentile"],
  "codes": ["600519", "000001"],
  "date": "2025-12-23"
}
```

---

*创建日期: 2025-12-23*
