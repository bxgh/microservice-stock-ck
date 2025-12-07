# EPIC-007 API 使用指南

## 快速开始

```python
from src.data_services import (
    QuotesService,
    TickService,
    HistoryService,
    RankingService,
    IndexService,
    SectorService,
    FinancialService,
    FundFlowService,
    get_time_strategy,
)
import asyncio

async def example():
    # 时段感知
    strategy = get_time_strategy()
    print(f"交易时段: {strategy.get_session()}")
    print(f"行情 TTL: {strategy.get_cache_ttl('quotes')}s")
```

---

## 服务使用示例

### 1. QuotesService - 实时行情

```python
service = QuotesService()
await service.initialize()

# 批量获取行情
df = await service.get_quotes(['600519', '000001'])
print(df[['code', 'name', 'price', 'change_pct']])

# 五档盘口
orderbook = await service.get_orderbook('600519')

await service.close()
```

### 2. TickService - 分笔成交

```python
service = TickService()
await service.initialize()

# 获取分笔数据
df = await service.get_tick('600519', '2025-12-06')
print(f"分笔数: {len(df)}")

await service.close()
```

### 3. HistoryService - 历史K线

```python
from src.data_services import HistoryService, AdjustType, Frequency

service = HistoryService()
await service.initialize()

# 日线 (前复权)
df = await service.get_daily(
    '600519',
    start='2025-01-01',
    end='2025-12-01',
    adjust=AdjustType.QFQ
)

await service.close()
```

### 4. RankingService - 榜单数据

```python
service = RankingService()
await service.initialize()

# 涨停池
limit_up = await service.get_limit_up_pool()

# 龙虎榜
lhb = await service.get_dragon_tiger()

await service.close()
```

### 5. IndexService - 指数/ETF

```python
service = IndexService()
await service.initialize()

# 沪深300成分股
stocks = await service.get_index_constituents('000300')

await service.close()
```

### 6. SectorService - 板块数据

```python
service = SectorService()
await service.initialize()

# 行业排行
df = await service.get_industry_ranking(limit=20)

# 板块成分股
stocks = await service.get_sector_stocks('半导体')

await service.close()
```

### 7. FinancialService - 财务报表

```python
service = FinancialService()
await service.initialize()

# 财务摘要
summary = await service.get_financial_summary('600519')

# PE/PB
pe_pb = await service.get_pe_pb('600519')

await service.close()
```

### 8. FundFlowService - 资金流向

```python
service = FundFlowService()
await service.initialize()

# 资金流向
flow = await service.get_fund_flow('600519', '2025-12-06')
print(f"大单净流入: {flow['large_net']:,.0f}")

await service.close()
```

---

## 时段感知策略

```python
from src.data_services import get_time_strategy

strategy = get_time_strategy()

# 时段判断
if strategy.is_trading_hours():
    print("盘中")
else:
    print("盘后")

# 动态 TTL
ttl = strategy.get_cache_ttl('quotes')  # 盘中3s, 盘后3600s

# 数据源优先级
sources = strategy.get_source_priority('ranking')
```

---

## 市场工具函数

```python
from src.data_services import (
    is_st_stock,
    get_price_limit,
    is_limit_up,
)

# ST股判断
is_st = is_st_stock('ST国华')  # True

# 涨跌幅限制
limit = get_price_limit('600519')  # 10%
limit = get_price_limit('ST国华')  # 5%

# 涨停判断
result = is_limit_up(11.0, 10.0, 'normal')  # True
```
