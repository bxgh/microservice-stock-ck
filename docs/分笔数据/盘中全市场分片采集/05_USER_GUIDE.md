# 05 用户手册：实时分笔数据使用指南

## 1. 数据库定义 (ClickHouse)

**库名**: `stock_data`  
**表名**: `tick_data_intraday`

| 字段 | 类型 | 说明 | 示例 |
|---|---|---|---|
| `stock_code` | String | 带市场前缀的代码 | `sz000001` |
| `trade_date` | Date | 交易日期 | `2026-01-21` |
| `tick_time` | String | 交易所时间 (HH:MM:SS) | `14:55:00` |
| `price` | Decimal | 成交价格 | `10.550` |
| `volume` | UInt32 | 单笔成交量 (手) | `1200` |
| `direction` | UInt8 | 成交方向 (0:买, 1:卖, 2:中性) | `0` |
| `created_at` | DateTime | 实际入库时间 (本地) | `2026-01-21 14:55:02` |

---

## 2. 常用分析 SQL

### 实时成交查询
```sql
-- 获取某股票最近 50 条分笔
SELECT * FROM stock_data.tick_data_intraday 
WHERE stock_code = 'sh600519' 
ORDER BY tick_time DESC, created_at DESC 
LIMIT 50;
```

### 资金流向初步统计
```sql
-- 计算某股票过去 10 分钟净买入量
SELECT 
    sum(price * volume) FILTER(WHERE direction = 0) as buy_amount,
    sum(price * volume) FILTER(WHERE direction = 1) as sell_amount
FROM stock_data.tick_data_intraday 
WHERE stock_code = 'sz000001' 
  AND created_at >= now() - INTERVAL 10 MINUTE;
```

---

## 3. 注意事项
*   **去重**: 由于 TDX 数据性质及多次拉取，可能会有极少量重复记录。建议在分析前使用 `SELECT DISTINCT` 或根据 `(tick_time, price, volume, direction)` 进行分组。
*   **清理**: 该表建议仅保留 7-14 天数据。过期数据会自动根据物理过期策略清理（如有配置）或需手动通过 `ALTER TABLE ... DELETE` 清理。
