# 分笔数据采集代码统一改进方案 (修订版 V1.2)

> **版本**: V1.2
> **更新时间**: 2026-01-23
> **状态**: 待评审

---

## 1. 问题审计结果 (Final)

### 1.1 核心问题清单

| # | 问题 | 严重程度 | 说明 | 现状 |
|---|------|---------|------|------|
| **P1** | API 路径错误 | 🔴 **严重** | `tick_worker.py` 使用 `/api/v1/ticks` (不存在) | 应为 `/api/v1/tick/{code}` |
| **P2** | 目标表命名混乱 | 🟡 中等 | `stock_tick_data_local` vs `tick_data_intraday` | 命名风格不统一，易混淆 |
| **P3** | Direction 字段映射 | 🟡 中等 | 此段逻辑不一致 | 需要统一为整数存储 |
| **P4** | 代码复用率低 | 🟡 中等 | 两个服务各自维护一套逻辑 | 需下沉至 `gsd-shared` |

---

## 2. 表结构详细分析 (针对 P2)

### 2.1 现状图谱

| 场景 | 服务 | 写入表 (Local) | 分布式表 (Distributed) | 用途 |
|------|------|----------------|------------------------|------|
| 盘中实时 | get-stockdata | `stock_tick_data_local` | `tick_data_intraday` | 当日高频查询 |
| 盘后当天 | gsd-worker | (无直接写入) | `tick_data_intraday` | 补全当日遗漏 |
| 盘后历史 | gsd-worker | (无直接写入) | `tick_data` | 历史归档数据 |

### 2.2 存在的问题

1. `get-stockdata` 写入的本地表名为 `stock_tick_data_local`，而对应的分布式表为 `tick_data_intraday`。
2. 命名不规范：建议统一使用 `tick_data_intraday` (分布式) 和 `tick_data_intraday_local` (本地)。

---

## 3. 改进方案

### Phase 0: 紧急修复 (立即执行)

> 目标：修复 P1 严重 Bug，确保盘中采集正常运行

**操作**:
修改 `services/get-stockdata/src/core/collector/components/tick_worker.py`:
```python
- url = f"{self.mootdx_api_url}/api/v1/ticks?code={code}"
+ url = f"{self.mootdx_api_url}/api/v1/tick/{code}"
```

---

### Phase 1: 统一字段映射与清洗 (1天)

> 目标：消除 P3 (Direction) 和 P4 (Prefix) 的差异

1. **Direction**: 统一映射为整数 (0=买, 1=卖, 2=中性)
   - mootdx-api 返回可能是String，需统一转换逻辑。
2. **Stock Code**: 统一使用 `gsd_shared` 的清洗逻辑 `clean_stock_code()`。

---

### Phase 2: 表名标准化 (2天)

> 目标：解决 P2，建立清晰的表命名规范

**新命名规范**:

| 用于 | 分布式表名 | 本地表名 |
|------|------------|----------|
| 当日数据 | `tick_data_intraday` | `tick_data_intraday_local` (原 `stock_tick_data_local`) |
| 历史数据 | `tick_data` | `tick_data_local` |

**迁移步骤**:
1. 创建新本地表 `tick_data_intraday_local`
2. 修改 `tick_data_intraday` 分布式表指向新本地表
3. 更新 `get-stockdata`Writer 写入新表
4. 数据迁移 (Optional, 当日数据可直接丢弃或归档)

---

### Phase 3: 共享模块重构 (3天)

> 目标：解决 P4，实现代码复用

新增 `libs/gsd-shared/gsd_shared/tick/` 模块：

```python
class TickFetcher:
    """
    统一采集器
    - mode=TODAY: /api/v1/tick/{code} (date=None)
    - mode=HISTORY: /api/v1/tick/{code} (date=YYYYMMDD)
    """

class TickWriter:
    """
    统一写入器
    - target=INTRADAY: 写入 tick_data_intraday (或 local)
    - target=HISTORY: 写入 tick_data
    """
```

---

## 4. 执行计划

1. **立即执行 Phase 0** (无需评审，Bug Fix)
2. Phase 1-3 待后续排期执行。

---

## 5. 验收标准

- `get-stockdata` 成功采集数据，无 404 错误。
- `gsd-worker` 补采使用相同的字段处理逻辑。
- 所有表命名符合 `*_local` 和 `*` (分布式) 的对应关系。
