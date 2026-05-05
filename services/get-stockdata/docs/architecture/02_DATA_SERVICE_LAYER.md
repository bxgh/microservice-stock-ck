# 数据服务逻辑层 (Data Service Layer)

**实现路径**: `src/data_services/`

## 1. 职责定位

Service 层处于 API 路由与底层的 Provider 之间。它的核心任务是执行“业务感知”逻辑，而非简单的透传数据。

- **多源聚合**: 从不同 Provider 获取碎片数据并组装。
- **降级保护 (Failover)**: 当主数据源（如 Mootdx）故障时，自动切换到备用源（如 Easyquotation）。
- **时效性控制**: 根据当前是否在交易时段，决定是从缓存读取还是强制刷新。

---

## 2. 核心服务组件

| 服务 | 实现文件 | 数据处理逻辑 |
| :--- | :--- | :--- |
| **QuotesService** | `quotes_service.py` | 负责实时快照和分笔。支持 L1/L2 数据的整合映射。 |
| **FinancialService** | `financial_service.py` | 财务报表、指标计算。支持跨年份数据的对齐与合并。 |
| **HistoryService** | `history_service.py` | K 线数据处理。负责前/后复权算法的实现。 |
| **ValuationService** | `valuation_service.py` | 估值计算。结合实时价格与财务报表计算动态 PE/PB。 |

---

## 3. 缓存策略实现

系统在 Service 层集成了缓存管理：

- **缓存键设计**: `f"{service_name}:{code}:{date}"`。
- **TTL 差异化**:
  - 实时快照: 3-5 秒 (交易时段)。
  - 静态信息/财务: 24 小时。
  - 行事历: 12 小时。

---

## 4. 并发与同步锁

为了防止在高并发请求下的“缓存击穿”，核心方法（如获取特定指标）通常配合 `asyncio.Lock` 使用：

```python
# 示例：src/data_services/base.py
async def get_with_lock(self, key, fetch_coro):
    async with self._lock:
        data = await self.cache.get(key)
        if not data:
            data = await fetch_coro()
            await self.cache.set(key, data)
        return data
```
