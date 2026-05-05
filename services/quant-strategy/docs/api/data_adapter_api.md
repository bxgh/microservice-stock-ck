# Data Adapter API 文档

## StockDataProvider

### 获取实时行情

```python
df = await data_provider.get_realtime_quotes(['600519', '000001'])
```

**返回**: DataFrame with `code`, `name`, `price`, `volume`, `change_pct`, `timestamp`

**缓存**: 5秒TTL

### 获取股票信息

```python
info = await data_provider.get_stock_info('600519')
```

**返回**: Dict with stock details

**缓存**: 7天TTL

## DataValidator 数据工具

```python
from adapters.data_utils import validate_quotes

df = validate_quotes(df)  # 验证数据完整性
```

## 性能

- 无缓存: ~12ms/股票
- 有缓存: ~3ms/股票 (4.2x提速)
