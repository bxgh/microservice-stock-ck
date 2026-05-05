# GSD-Shared

股票数据平台共享数据模型库，为 gsd-api 和 gsd-worker 提供统一的数据模型定义。

## 安装

### 开发模式（推荐）

```bash
cd libs/gsd-shared
pip install -e .
```

### 生产模式

```bash
cd libs/gsd-shared
python -m build
pip install dist/gsd_shared-0.1.0-py3-none-any.whl
```

## 使用

```python
from gsd_shared.models import KLineRecord, StockInfo

# 从 MySQL 数据创建 K线记录
mysql_row = {
    'code': '000001',
    'trade_date': '2024-01-02',
    'open': 10.5,
    # ...
}
record = KLineRecord.from_mysql(mysql_row)

# 转换为 ClickHouse 插入格式
ch_dict = record.to_clickhouse_dict()
```

## 核心模型

- **KLineRecord**: K线数据模型
- **StockInfo**: 股票基础信息模型
- **SyncRecord**: 同步任务记录模型

## 版本

当前版本: 0.1.0
