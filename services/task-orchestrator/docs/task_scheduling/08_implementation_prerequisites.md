# 实施前核心问题检查报告

## 检查结果

### ✅ 1. Pydantic 版本

```
当前版本: pydantic==2.5.0
状态: ✅ 兼容
```

**结论**: 使用 Pydantic v2，需注意：
- 使用 `Field(..., description="")` 语法
- 使用 `model_validate()` 而非 `parse_obj()`
- 配置使用 `model_config` 或 `class Config`

---

### ✅ 2. MySQL vs ClickHouse 字段映射

#### MySQL 表字段 (from `sync_service.py`)
```sql
code, trade_date, open, high, low, close, volume, amount, turnover, pct_chg
```

#### ClickHouse 表字段 (from `clickhouse_kline_ddl.sql`)
```sql
stock_code, trade_date, open_price, high_price, low_price, close_price, 
volume, amount, turnover_rate, change_pct
```

#### 字段映射表

| MySQL | ClickHouse | gsd-shared 模型 | 说明 |
|:------|:-----------|:----------------|:-----|
| `code` | `stock_code` | `stock_code` | ✅ 需映射 |
| `trade_date` | `trade_date` | `trade_date` | ✅ 一致 |
| `open` | `open_price` | `open_price` | ✅ 需映射 |
| `high` | `high_price` | `high_price` | ✅ 需映射 |
| `low` | `low_price` | `low_price` | ✅ 需映射 |
| `close` | `close_price` | `close_price` | ✅ 需映射 |
| `volume` | `volume` | `volume` | ✅ 一致 |
| `amount` | `amount` | `amount` | ✅ 一致 |
| `turnover` | `turnover_rate` | `turnover_rate` | ✅ 需映射 |
| `pct_chg` | `change_pct` | `change_pct` | ✅ 需映射 |

---

## 解决方案：数据适配器

```python
# gsd_shared/models/kline.py
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class KLineRecord(BaseModel):
    """K线数据记录 - 统一模型"""
    stock_code: str
    trade_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    amount: float
    turnover_rate: Optional[float] = None
    change_pct: Optional[float] = None
    
    @classmethod
    def from_mysql(cls, row: dict):
        """从 MySQL 行数据创建（字段名映射）"""
        return cls(
            stock_code=row['code'],
            trade_date=row['trade_date'],
            open_price=row['open'],
            high_price=row['high'],
            low_price=row['low'],
            close_price=row['close'],
            volume=row['volume'],
            amount=row['amount'],
            turnover_rate=row.get('turnover'),
            change_pct=row.get('pct_chg')
        )
    
    def to_clickhouse_dict(self) -> dict:
        """转换为 ClickHouse 插入所需的字典"""
        return {
            'stock_code': self.stock_code,
            'trade_date': self.trade_date,
            'open_price': self.open_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'close_price': self.close_price,
            'volume': self.volume,
            'amount': self.amount,
            'turnover_rate': self.turnover_rate,
            'change_pct': self.change_pct
        }
```

---

## 使用示例

### 在 gsd-worker 中使用

```python
# gsd-worker/src/jobs/sync.py
from gsd_shared.models import KLineRecord

async def sync_kline():
    # 从 MySQL 读取
    rows = await fetch_from_mysql()
    
    # 转换为统一模型
    records = [KLineRecord.from_mysql(row) for row in rows]
    
    # 插入到 ClickHouse
    for record in records:
        await ch_client.execute(
            "INSERT INTO stock_kline_daily VALUES",
            [record.to_clickhouse_dict()]
        )
```

---

## 迁移策略

**阶段 1**: 创建 gsd-shared，与现有代码并存  
**阶段 2**: gsd-worker 和 gsd-api 逐步引入  
**阶段 3**: get-stockdata 作为兼容层  

**时间线**: 2-3 周完成
