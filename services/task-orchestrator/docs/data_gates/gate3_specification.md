# 盘后门禁 (Gate-3) 设计规范

**文档版本**: 2.0  
**最后更新**: 2026-01-17  
**状态**: 已实现

---

## 1. 核心原则

Gate-3 是整个数据系统的**决策层**，负责审计和决策，Worker 只负责执行。

**关键要求**：
1. Gate-3 必须在审计阶段就计算出需要补采的股票列表
2. 任务参数必须携带具体股票代码，Worker 不再重新查询
3. 所有数据源必须使用 K线数据作为"实际交易股票"的真理来源

---

## 2. 时间规则

| 当前时间 | 目标交易日 |
| :--- | :--- |
| **< 6:00 AM** | 前一日 |
| **≥ 6:00 AM** | 当日 |

**实现**: `_get_target_trading_date()` 方法

---

## 3. 覆盖率计算规范

### 3.1 K线覆盖率

| 项目 | 说明 |
| :--- | :--- |
| **分子** | ClickHouse `stock_kline_daily` 当日去重股票数 |
| **分母** | MySQL `stock_kline_daily` 当日记录数 |
| **公式** | `ClickHouse / MySQL × 100%` |
| **阈值** | < 98% 触发修复 |

### 3.2 分笔覆盖率

| 项目 | 说明 |
| :--- | :--- |
| **分子** | ClickHouse `tick_data` 当日去重股票数 |
| **分母** | **ClickHouse `stock_kline_daily` 当日去重股票数** |
| **公式** | `Tick股票数 / K线股票数 × 100%` |
| **阈值** | < 95% 触发修复 |

> ⚠️ **禁止使用 Redis 静态名单作为分母**

---

## 4. 股票代码格式规范

| 场景 | 格式 | 示例 |
| :--- | :--- | :--- |
| K线表 | 可能带前缀 | `sh600000`, `sz000001` |
| Tick表 | 纯代码 | `600000`, `000001` |
| 任务参数 | **必须纯代码** | `000001,000002,600001` |

**处理逻辑**: 从 K线表获取代码后，自动移除 `sh/sz` 前缀

---

## 5. 决策层架构

```
Gate-3 审计
  ↓
_check_all_ticks_continuity() → 返回 failed_codes 列表
  ↓
_process_tiered_repair() → 按 Shard 分组 (failed_by_shard)
  ↓
_trigger_shard_repair(date, shard_id, shard_failed)
  ↓
插入任务: {"date": "20260116", "shard_id": 0, "stock_codes": "000001,000002,..."}
  ↓
Worker 直接执行，无需再查询
```

**禁止行为**:
- ❌ `_trigger_shard_repair(date, shard_id, None)` - 不允许传 None
- ❌ Worker 运行时重新查询 ClickHouse 确定补采范围

---

## 6. 分级修复策略

| 异常数量 | 策略 | 任务类型 | 参数 |
| :--- | :--- | :--- | :--- |
| **1-50** | 单点精准 | `stock_data_supplement` | `{"stocks": [...], "data_types": ["tick"]}` |
| **51-200** | 分片并行 | `stock_data_supplement` × 3 | 按 `xxhash % 3` 分组 |
| **> 200** | 分片定向 | `repair_tick` × 3 | **每个 Shard 携带该分片的 failed_codes** |

**关键**: 即使异常数量 > 200，也必须使用**定向补采**（携带具体列表），而不是全量扫描

---

## 7. 实现检查清单

- [x] 6AM 规则 (`_get_target_trading_date`)
- [x] 分笔覆盖率使用 K线作为分母 (`_check_tick_coverage`)
- [x] 统一使用预计算的 failed_codes 列表 (`_process_tiered_repair`)
- [x] 股票代码格式标准化 (`_get_stocks_from_kline`)
- [x] 去重窗口防止重复任务 (`_trigger_shard_repair`)

---

## 8. 相关 Commits

| Commit | 描述 |
| :--- | :--- |
| `4ba01fd` | 分笔覆盖率改用K线作为分母 |
| `77d32db` | 统一使用预计算的 failed_codes 列表 |
| `bad4cf5` | 修复误报离线问题 |
| `7cc133d` | 添加缺失的 timedelta 导入 |
| `f5bece7` | 优化分布式补采系统 |
