# GSD-Shared 共享库设计

> **目的**: 为 gsd-api 和 gsd-worker 提供统一的数据模型、常量定义和工具函数。

---

## 1. 为什么需要 gsd-shared？

### 问题场景

```python
# ❌ 没有共享库的问题
# gsd-worker/src/models.py
class KLineRecord:
    trade_date: str  # 定义为字符串

# gsd-api/src/models.py  
class KLineRecord:
    trade_date: date  # 定义为日期对象

# 结果：两边类型不一致，容易出错！
```

### 解决方案

```python
# ✅ 使用共享库
# libs/gsd-shared/gsd_shared/models/kline.py
class KLineRecord(BaseModel):
    trade_date: date  # 统一定义

# gsd-worker 和 gsd-api 都引用这个
from gsd_shared.models import KLineRecord
```

---

## 2. 目录结构

```
libs/gsd-shared/
├── gsd_shared/
│   ├── __init__.py
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   ├── kline.py         # K线模型
│   │   ├── stock.py         # 股票基础信息
│   │   ├── market.py        # 市场行情
│   │   └── sync.py          # 同步状态模型
│   ├── constants.py         # 常量定义
│   └── utils/               # 工具函数
│       ├── __init__.py
│       └── time_utils.py    # 时间处理工具
├── pyproject.toml
├── README.md
└── tests/
    └── test_models.py
```

---

## 3. 核心模型定义

### 3.1 K线模型

**基于现有 ClickHouse 表结构**: `stock_kline_daily`

```python
# gsd_shared/models/kline.py
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class KLineRecord(BaseModel):
    """K线数据记录 - 与 ClickHouse stock_kline_daily 表结构一致"""
    stock_code: str = Field(..., description="股票代码（6位）")
    trade_date: date = Field(..., description="交易日期")
    open_price: float = Field(..., description="开盘价")
    high_price: float = Field(..., description="最高价")
    low_price: float = Field(..., description="最低价")
    close_price: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量（股）")
    amount: float = Field(..., description="成交额（元）")
    turnover_rate: Optional[float] = Field(None, description="换手率（%）")
    change_pct: Optional[float] = Field(None, description="涨跌幅（%）")
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }
```

### 3.2 股票信息模型

**基于现有实现**: `services/get-stockdata/src/models/stock_models.py`

```python
# gsd_shared/models/stock.py
from datetime import datetime
from typing import Optional

class StockCodeMapping(BaseModel):
    """股票代码映射信息"""
    standard: str
    tushare: str
    akshare: str
    tonghua_shun: str
    wind: str
    east_money: str

class StockInfo(BaseModel):
    """股票基础信息"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    exchange: str = Field(..., description="交易所 (SH|SZ|BJ)")
    asset_type: str = Field("stock", description="资产类型")
    is_active: bool = Field(True, description="是否活跃")
    code_mappings: StockCodeMapping
    list_date: Optional[datetime] = None
    delist_date: Optional[datetime] = None
    industry: Optional[str] = None
    sector: Optional[str] = None
    market_cap: Optional[float] = None  # 总市值(亿元)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
```

### 3.3 同步状态模型

```python
# gsd_shared/models/sync.py
from enum import Enum

class SyncStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    
class SyncRecord(BaseModel):
    """同步任务记录"""
    task_id: str
    status: SyncStatus
    start_time: datetime
    end_time: Optional[datetime]
    total_count: int
    success_count: int
    failed_count: int
```

---

## 4. 常量定义

```python
# gsd_shared/constants.py

# 交易所代码
class Exchange:
    SH = "SH"  # 上海
    SZ = "SZ"  # 深圳
    BJ = "BJ"  # 北京

# 交易时间
TRADING_HOURS = {
    "morning": ("09:30", "11:30"),
    "afternoon": ("13:00", "15:00")
}

# 数据质量阈值
QUALITY_THRESHOLDS = {
    "completeness": 0.95,  # 完整性 >= 95%
    "max_missing": 50       # 最多缺失50只
}
```

---

## 5. 使用方式

### 5.1 安装

```toml
# gsd-worker/pyproject.toml
[project]
dependencies = [
    "gsd-shared @ file:///${PROJECT_ROOT}/../../libs/gsd-shared"
]
```

或通过开发模式安装：
```bash
cd services/gsd-worker
pip install -e ../../libs/gsd-shared
```

### 5.2 在代码中使用

```python
# gsd-worker/src/jobs/sync.py
from gsd_shared.models import KLineRecord, SyncStatus
from gsd_shared.constants import QUALITY_THRESHOLDS

async def sync_kline():
    records = []
    for row in fetch_from_mysql():
        record = KLineRecord(**row)
        records.append(record)
    
    await save_to_clickhouse(records)
    
    # 使用共享常量
    if len(records) < QUALITY_THRESHOLDS["max_missing"]:
        return SyncStatus.SUCCESS
```

---

## 6. 版本管理

```toml
# pyproject.toml
[project]
name = "gsd-shared"
version = "0.1.0"
```

**版本策略**：
- 破坏性变更：主版本号 +1
- 新增字段：次版本号 +1
- Bug修复：补丁版本号 +1

---

## 7. 测试

```python
# tests/test_kline.py
import pytest
from datetime import date
from gsd_shared.models import KLineRecord

def test_kline_creation():
    record = KLineRecord(
        stock_code="000001",
        trade_date=date(2024, 1, 2),
        open=10.5,
        high=11.0,
        low=10.2,
        close=10.8,
        volume=1000000,
        amount=10800000
    )
    assert record.stock_code == "000001"
    assert record.close == 10.8
```

---

## 8. 发布流程

1. 更新版本号
2. 运行测试: `pytest`
3. 构建包: `python -m build`
4. 两个服务重新安装: `pip install -e ../../libs/gsd-shared --force-reinstall`
