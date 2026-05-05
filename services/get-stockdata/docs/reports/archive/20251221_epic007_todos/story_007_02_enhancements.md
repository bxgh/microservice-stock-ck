# Story 007.02 未完成优化项

**创建日期**: 2025-12-06  
**优先级**: P1-P2  
**状态**: 待实现

---

## P1 优化项（推荐下次迭代）

### 1. 批量分片查询策略

**目的**: 优化大批量股票查询性能和成功率

**当前问题**:
- 一次查询1000只股票耗时8.5秒
- 成功率较低（只返回53%数据）
- 单批量失败影响全部结果

**解决方案**: 实现 `get_quotes_batched()` 方法

**实现参考**:
```python
async def get_quotes_batched(
    self,
    codes: List[str],
    batch_size: int = 100,
    max_concurrent: int = 5
) -> pd.DataFrame:
    """分批查询股票行情（并发执行）
    
    将大批量查询拆分成小批量，提高成功率和性能。
    
    Args:
        codes: 股票代码列表
        batch_size: 每批数量，默认100
        max_concurrent: 最大并发数，默认5
        
    Returns:
        pd.DataFrame: 合并后的行情数据
        
    Example:
        # 查询1000只股票
        df = await service.get_quotes_batched(codes, batch_size=100)
        # 预计耗时: ~0.3秒 (vs 当前8.5秒)
    """
    # 实现逻辑见 test_report.md
```

**预期改善**:
- ✅ 性能提升 20-30倍 (8.5s → 0.3s)
- ✅ 成功率提升到 95%+
- ✅ 失败隔离（单批失败不影响其他）

**工作量**: 2-3小时

**参考文档**: `/home/bxgh/.gemini/antigravity/brain/.../test_report.md` (P1优化建议)

---

### 2. 全市场查询实现

**目的**: 实现 `get_all_quotes()` 全市场行情查询

**当前状态**: 
```python
async def get_all_quotes(self):
    # 当前返回空 DataFrame
    logger.warning("All market quotes not available, using fallback")
    return pd.DataFrame()
```

**解决方案**:

**选项 A**: 加载全市场股票代码
```python
def _load_all_stock_codes(self) -> List[str]:
    """从配置文件/数据库加载全市场股票代码"""
    # 从 tushare/akshare 获取所有A股代码
    # 或从本地配置文件读取
    return all_codes

async def get_all_quotes(self):
    codes = self._load_all_stock_codes()
    return await self.get_quotes_batched(codes, batch_size=100)
```

**选项 B**: 使用 easyquotation 全市场接口
```python
async def get_all_quotes(self):
    result = await self._data_manager.get_quotes(
        codes=[],  # 空列表表示全市场
        all_market=True
    )
    return self._standardize_quotes(result.data)
```

**工作量**: 1-2小时

---

### 3. 缓存预热机制

**目的**: 交易日开盘前预加载热门股票

**使用场景**:
- 开盘前缓存沪深300成分股
- 缓存用户关注的股票池
- 定时刷新热门股票

**实现方案**:
```python
async def warmup_cache(self, stock_pools: List[str] = None):
    """缓存预热
    
    Args:
        stock_pools: 股票池列表，如 ['hs300', 'zz500', 'custom']
    """
    if stock_pools is None:
        stock_pools = ['hs300']  # 默认沪深300
    
    codes = []
    for pool in stock_pools:
        codes.extend(self._get_pool_codes(pool))
    
    # 预加载
    await self.get_quotes(codes)
    logger.info(f"✅ Cache warmed up: {len(codes)} stocks")
```

**定时任务**:
```python
# 在 main.py 中添加
@scheduler.scheduled_job('cron', hour=9, minute=15)  # 开盘前15分钟
async def warmup_quotes_cache():
    await quotes_service.warmup_cache(['hs300', 'zz500'])
```

**工作量**: 1小时

---

## P2 优化项（可选）

### 4. 增强文档字符串示例

**目的**: 改善API可用性

**当前状态**: 部分方法缺少 Examples 节

**改进示例**:
```python
async def get_quotes(self, codes: List[str]) -> pd.DataFrame:
    """获取实时行情（批量）
    
    Args:
        codes: 股票代码列表
        
    Returns:
        pd.DataFrame: 标准化行情数据
        
    Examples:
        >>> service = QuotesService()
        >>> await service.initialize()
        >>> 
        >>> # 查询3只股票
        >>> df = await service.get_quotes(['000001', '600519', '000858'])
        >>> print(df[['code', 'name', 'price', 'change_pct']])
        >>>
        >>> # 查看统计
        >>> stats = service.get_stats()
        >>> print(f"缓存命中率: {stats['cache_hit_rate']}")
    """
```

**工作量**: 2小时

---

### 5. Prometheus 监控指标

**目的**: 集成监控系统

**指标设计**:
```python
from prometheus_client import Counter, Histogram

# 请求计数
quotes_requests_total = Counter(
    'quotes_requests_total',
    'Total quotes requests',
    ['status']  # success/failure
)

# 响应时间
quotes_response_time = Histogram(
    'quotes_response_time_seconds',
    'Quotes response time'
)

# 缓存命中率
quotes_cache_hit_rate = Gauge(
    'quotes_cache_hit_rate',
    'Cache hit rate'
)
```

**工作量**: 3-4小时

---

### 6. 换手率计算

**目的**: 补充换手率字段（需要流通股本数据）

**依赖**: MetaService（Story 007.05）

**实现**:
```python
async def _calculate_turnover(self, df: pd.DataFrame) -> pd.DataFrame:
    """计算换手率
    
    公式: 换手率 = 成交量 / 流通股本 × 100%
    """
    # 获取流通股本
    codes = df['code'].tolist()
    meta = await self._meta_service.get_stock_meta(codes)
    
    # 计算换手率
    df = df.merge(meta[['code', 'float_shares']], on='code')
    df['turnover'] = (df['volume'] * 100 / df['float_shares'] * 100)
    
    return df
```

**工作量**: 需要先完成 MetaService

---

## 实施计划建议

### 短期（本周）
- ✅ **无** - Story 007.02 已完成并通过质控

### 中期（下周）
- [ ] **P1-1**: 批量分片查询策略（预计2-3小时）
- [ ] **P1-2**: 全市场查询实现（预计1-2小时）

### 长期（下月）
- [ ] **P1-3**: 缓存预热机制
- [ ] **P2-4**: 文档字符串增强
- [ ] **P2-5**: Prometheus 监控

---

## 参考文档

- 实施报告: `walkthrough.md`
- 代码质控: `qa_report.md`
- 测试报告: `test_report.md`
- 性能数据: `test_report.md` 性能基准测试章节

---

**维护人**: EPIC-007 Team  
**最后更新**: 2025-12-06
