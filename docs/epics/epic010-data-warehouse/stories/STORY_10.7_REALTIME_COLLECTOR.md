# Story 10.7: 实时行情采集

## Story 信息

| 字段 | 值 |
|------|-----|
| **Story ID** | 10.7 |
| **所属 Epic** | EPIC-010 本地数据仓库 |
| **优先级** | P2 |
| **预估工时** | 4 天 |
| **前置依赖** | Story 10.0 |

---

## 目标

实现从 Mootdx 采集实时行情，写入 Redis 缓存，支持低延迟访问。

---

## 验收标准

1. ✅ 交易时间内实时采集行情
2. ✅ 行情写入 Redis，TTL 3 秒
3. ✅ 支持批量查询实时价格
4. ✅ 采集延迟 < 1 秒

---

## 任务分解

### Task 1: Mootdx 采集器

```python
# src/collectors/mootdx.py
class MootdxCollector:
    async def collect_realtime(self, codes: list[str]) -> list[dict]:
        """采集实时行情"""
        pass
```

### Task 2: Redis 写入

```python
# src/writers/redis.py
class RedisQuoteWriter:
    async def write_quotes(self, quotes: list[dict]):
        """批量写入行情，key=quote:{code}，TTL=3s"""
        pass
```

### Task 3: 交易时间控制

```python
# 仅在交易时间采集
# 09:30-11:30, 13:00-15:00 (Asia/Shanghai)
```

---

*创建日期: 2025-12-23*
