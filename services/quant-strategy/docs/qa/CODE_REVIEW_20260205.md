# Git Diff 代码质控报告

**日期**: 2026-02-05  
**检查范围**: Epic-002 Part 1 所有新增和修改文件  
**质控人**: Antigravity Agent

---

## ✅ 符合规范项

### 1. 中文注释规范 ✓
- 所有 Python 文件模块级 docstring 使用中文
- 关键函数均有中文注释说明用途
- 文档 `epic_part_1_foundation.md` 全程中文

### 2. 代码结构 ✓
- 遵循单一职责原则 (Cleaner/Engine/Gatekeeper 分离)
- 使用类型提示 (`pd.DataFrame`, `Optional`, `Dict` 等)
- 异常处理覆盖所有外部调用 (ClickHouse 查询)

### 3. 资源管理 ✓
- `ClickHouseLoader` 提供 `close()` 方法
- 所有 Engine 使用完毕后正确调用 `loader.close()`

---

## ⚠️ 需修复的高风险问题

### 🔴 P0: SQL 注入风险 (Critical)

**文件**: `src/adapters/clickhouse_loader.py`  
**位置**: Line 54-58, Line 98-100

**问题代码**:
```python
query = f"""
    SELECT ...
    FROM {self.snapshot_table}
    WHERE stock_code = '{stock_code}'
      AND toDate(trade_date) = '{trade_date}'
"""
```

**风险**: 
- `stock_code` 和 `trade_date` 直接拼接到 SQL，存在注入风险
- 恶意输入如 `stock_code = "'; DROP TABLE tick_data; --"` 可导致数据库破坏

**修复方案**:
```python
# 使用参数化查询
query = """
    SELECT ...
    FROM %(table)s
    WHERE stock_code = %(code)s
      AND toDate(trade_date) = %(date)s
"""
data, columns = self.client.execute(
    query, 
    {'table': self.snapshot_table, 'code': stock_code, 'date': trade_date}
)
```

**或** 使用 `clickhouse-driver` 的占位符:
```python
query = f"""
    SELECT ... FROM {self.snapshot_table}
    WHERE stock_code = %s AND toDate(trade_date) = %s
"""
data, columns = self.client.execute(query, [stock_code, trade_date])
```

---

### 🟡 P1: 类型转换安全性

**文件**: `src/core/features/basic_engine.py`  
**位置**: Line 112, Line 125

**问题**:
```python
df['current_price'] = df['current_price'].astype(float)
open_price = float(df['current_price'].iloc[0])
```

**风险**: 
- 如果 ClickHouse 返回 `None` 或非数值，`astype(float)` 会抛出异常
- `iloc[0]` 未检查 DataFrame 是否为空

**修复方案**:
```python
# 添加空值检查
if df.empty or df['current_price'].iloc[0] is None:
    logger.warning("...")
    return pd.Series(dtype=float)
    
df['current_price'] = pd.to_numeric(df['current_price'], errors='coerce').fillna(0).astype(float)
```

---

### 🟡 P1: 时间边界处理

**文件**: `src/core/etl/cleaner.py`  
**位置**: Line 58

**问题**:
```python
full_grid = morning_range[1:].union(afternoon_range[1:])
```

**逻辑隐患**:
- `[1:]` 跳过第一个时间点 (09:30, 13:00)
- 这与设计文档"09:31-11:30, 13:01-15:00"一致，但如果集合竞价数据丢失会导致首分钟量异常

**建议**: 添加注释说明集合竞价处理逻辑

---

## 🟢 优化建议

### 1. 性能优化

**文件**: `src/core/features/trade_size_engine.py`  
**建议**: 
- Line 46-51 的向量化 `resample` 逻辑高效，无需修改
- 如批量处理 5000+ 股票，考虑使用 `multiprocessing.Pool`

### 2. 日志增强

**所有 Engine 文件**:
- 当前仅在异常时记录错误
- 建议增加 `logger.info` 记录处理进度 (如 "Processing {stock_code}...")

### 3. 配置验证

**文件**: `src/config/settings.py`  
**建议**:
```python
# 添加 ClickHouse 连接验证
@validator('QS_CLICKHOUSE_HOST')
def validate_host(cls, v):
    if not v or v == '':
        raise ValueError("ClickHouse host cannot be empty")
    return v
```

---

## 📋 修复优先级

| 优先级 | 问题 | 影响范围 | 建议修复时间 |
|:---:|:---|:---|:---|
| **P0** | SQL 注入风险 | 生产环境安全 | **立即** |
| **P1** | 类型转换安全 | 数据异常时崩溃 | 24小时内 |
| **P1** | 时间边界逻辑 | 首分钟数据准确性 | 本周内 |
| **P2** | 日志不足 | 可观测性 | 有空时 |

---

## 总结

**代码质量评分**: 7.5/10

**优点**:
- 架构清晰，符合单一职责
- 注释完整，满足中文规范
- 异常处理覆盖率高

**核心风险**:
- **SQL 注入** 必须立即修复，否则禁止上线

**建议下一步**:
1. 修复 SQL 注入漏洞
2. 添加单元测试覆盖边界情况
3. 对接 Linter (`pylint`, `mypy`) 进行静态检查
