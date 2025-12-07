# QuotesService API 文档

**服务**: 实时行情服务  
**模块**: `src.data_services.QuotesService`  
**版本**: 1.0.0  
**作者**: EPIC-007 Story 007.02

---

## 概述

QuotesService 是数据中台的核心服务之一，提供统一的实时行情数据访问接口。

**核心特性**:
- ✅ 多数据源自动降级 (mootdx → easyquotation)
- ✅ 智能缓存 (盘中3s / 盘后1h / 非交易日1d)
- ✅ 字段标准化 (QuoteSchema)
- ✅ 10+ 查询方法

---

## 快速开始

```python
from src.data_services import QuotesService

# 初始化
service = QuotesService()
await service.initialize()

# 查询行情
df = await service.get_quotes(['000001', '600519'])
print(df[['code', 'name', 'price', 'change_pct']])

# 清理
await service.close()
```

---

## API 参考

### 核心查询方法

#### get_quotes(codes, use_cache=True)
批量获取实时行情

**参数**:
- `codes` (List[str]): 股票代码列表，最多1000只
- `use_cache` (bool): 是否使用缓存，默认True

**返回**: `pd.DataFrame` - 标准化行情数据

**异常**:
- `ValueError`: codes 参数为空
- `RuntimeError`: 所有数据源失败

**示例**:
```python
df = await service.get_quotes(['000001', '600519', '000858'])
# 返回字段: code, name, price, open, high, low, close, volume, amount, change_pct
```

---

#### get_quote(code)
获取单个股票行情（便捷方法）

**参数**:
- `code` (str): 股票代码

**返回**: `pd.Series | None` - 单个股票行情，失败返回None

**示例**:
```python
quote = await service.get_quote('000001')
if quote:
    print(f"{quote['name']}: {quote['price']:.2f} ({quote['change_pct']:.2f}%)")
```

---

#### get_all_quotes(use_cache=True)
获取全市场行情

**参数**:
- `use_cache` (bool): 是否使用缓存

**返回**: `pd.DataFrame` - 全市场行情

**注意**: 当前返回空DataFrame，需要实现（见 TODO）

---

#### get_quotes_with_orderbook(codes, use_cache=True)
获取带五档盘口的行情数据

**参数**:
- `codes` (List[str]): 股票代码列表
- `use_cache` (bool): 是否使用缓存

**返回**: `pd.DataFrame` - 包含五档盘口的行情

**额外字段**: bid_price1-5, bid_volume1-5, ask_price1-5, ask_volume1-5

---

### 筛选方法

#### get_top_gainers(n=50)
获取涨幅前N名

**参数**:
- `n` (int): 返回数量，默认50

**返回**: `pd.DataFrame`

---

#### get_top_losers(n=50)
获取跌幅前N名

---

#### get_top_volume(n=50)
获取成交量前N名

---

#### get_limit_up_stocks()
获取涨停股票（涨幅 >= 9.9%）

---

#### get_limit_down_stocks()
获取跌停股票（涨幅 <= -9.9%）

---

#### get_quotes_by_change_pct(min_pct=None, max_pct=None)
按涨跌幅范围筛选

**参数**:
- `min_pct` (float): 最小涨跌幅（%）
- `max_pct` (float): 最大涨跌幅（%）

**示例**:
```python
# 涨幅5%-10%的股票
df = await service.get_quotes_by_change_pct(5.0, 10.0)
```

---

### 工具方法

#### get_quotes_dict(codes)
获取字典格式的行情数据

**返回**: `Dict[str, Dict]` - {code: {price, name, ...}}

---

#### get_stats()
获取统计信息

**返回**: 
```python
{
    'total_requests': 100,
    'cache_hits': 80,
    'cache_misses': 20,
    'provider_calls': 20,
    'failed_requests': 0,
    'cache_hit_rate': '80.0%'
}
```

---

#### clear_cache(pattern='quotes:*')
清除缓存

**参数**:
- `pattern` (str): 缓存键模式，支持 * 通配符

---

## 数据格式

### QuoteSchema 标准字段

| 字段 | 类型 | 说明 | 必需 |
|------|------|------|------|
| code | str | 股票代码 (6位) | ✅ |
| name | str | 股票名称 | ✅ |
| price | float | 最新价 | ✅ |
| open | float | 开盘价 | ✅ |
| high | float | 最高价 | ✅ |
| low | float | 最低价 | ✅ |
| close | float | 收盘价 | ✅ |
| pre_close | float | 昨收价 | ✅ |
| volume | float | 成交量（手）| ✅ |
| amount | float | 成交额（元）| ✅ |
| change | float | 涨跌额（元）| ✅ |
| change_pct | float | 涨跌幅（%）| ✅ |
| turnover | float | 换手率（%）| ❌ |

---

## 缓存策略

### 时段感知TTL

| 时段 | TTL | 说明 |
|------|-----|------|
| 盘中 (9:30-15:00) | 3秒 | 高频更新 |
| 盘后 (15:00-次日9:30) | 1小时 | 数据不变 |
| 非交易日 | 1天 | 长期缓存 |

### 缓存键格式

```
quotes:batch:{hash}              # 批量查询
quotes:all_market               # 全市场
quotes_ob:batch:{hash}          # 带盘口
```

---

## 性能指标

| 场景 | 性能 | 状态 |
|------|------|------|
| 100只股票（无缓存）| ~100ms | ✅ |
| 100只股票（缓存）| ~34ms | ✅ |
| 1000只股票 | ~8.5s | ⚠️ 待优化 |
| 缓存命中率 | 80%+ | ✅ |
| 并发10请求 | 全通过 | ✅ |

---

## 最佳实践

### 1. 资源管理
```python
# ✅ 推荐：使用 async with
async with QuotesService() as service:
    df = await service.get_quotes(codes)

# 或手动管理
service = QuotesService()
try:
    await service.initialize()
    df = await service.get_quotes(codes)
finally:
    await service.close()
```

### 2. 错误处理
```python
try:
    df = await service.get_quotes(codes)
except ValueError as e:
    logger.error(f"参数错误: {e}")
except RuntimeError as e:
    logger.error(f"查询失败: {e}")
```

### 3. 性能优化
```python
# ✅ 利用缓存
df1 = await service.get_quotes(codes)  # 第一次查询
df2 = await service.get_quotes(codes)  # 命中缓存，极快

# ✅ 批量查询优于多次单查
df = await service.get_quotes(['000001', '000002', '000003'])  # ✅ 好
# vs
df1 = await service.get_quote('000001')  # ❌ 慢
df2 = await service.get_quote('000002')
df3 = await service.get_quote('000003')
```

---

## 常见问题

**Q: 为什么1000只股票查询这么慢？**  
A: 数据源限制，建议使用批量分片策略（见 TODO）。100只以内性能最佳。

**Q: 如何提高缓存命中率？**  
A: 使用缓存预热机制，开盘前预加载常用股票池。

**Q: 换手率字段为何总是None？**  
A: 需要流通股本数据，待 MetaService 完成后实现。

---

## 相关文档

- [实施报告](../walkthrough.md)
- [测试报告](../test_report.md)
- [优化TODO](../todo/story_007_02_enhancements.md)

---

**最后更新**: 2025-12-06
