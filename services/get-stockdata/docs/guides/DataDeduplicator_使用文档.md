# DataDeduplicator 使用文档

## 概述

DataDeduplicator 是一个高效、灵活的数据去重处理器，专为大数据量场景设计。它支持多种去重策略和自定义键函数，能够满足各种数据清洗需求。

## 核心特性

### 🚀 高性能表现
- **单字段去重**: 10万条数据 < 0.03秒
- **多字段去重**: 10万条数据 < 0.06秒
- **统计信息生成**: 10万条数据 < 0.11秒
- **准确率**: 100%

### 🎯 多种去重策略
- **FIRST**: 保留第一次出现的记录
- **LAST**: 保留最后一次出现的记录
- **RANDOM**: 随机保留一条记录

### 🔧 灵活的键定义
- 单字段去重
- 多字段组合去重
- 自定义函数去重

## 快速开始

### 基础用法

```python
import pandas as pd
from core.data_deduplicator import DataDeduplicator, DeduplicationStrategy

# 创建去重器实例
deduplicator = DataDeduplicator()

# 准备测试数据
df = pd.DataFrame({
    'id': [1, 2, 1, 3, 2, 4],
    'value': ['A', 'B', 'A', 'C', 'B', 'D'],
    'price': [10.0, 20.0, 10.0, 30.0, 20.0, 40.0]
})

# 单字段去重（保留首次出现）
result = deduplicator.remove_duplicates(
    df,
    key_columns=['id'],
    strategy=DeduplicationStrategy.FIRST
)

print(f"去重前: {len(df)} 条记录")
print(f"去重后: {len(result)} 条记录")
```

### 多字段组合去重

```python
# 基于多个字段的组合去重
result = deduplicator.remove_duplicates(
    df,
    key_columns=['id', 'value'],
    strategy=DeduplicationStrategy.LAST  # 保留最后一次出现
)
```

### 自定义函数去重

```python
# 使用自定义函数生成复合键
def custom_key(row):
    return f"{row['id']}_{row['price'] > 15}"

result = deduplicator.deduplicate_by_key(
    df,
    key_func=custom_key,
    strategy=DeduplicationStrategy.FIRST
)
```

## API 参考

### DataDeduplicator 类

#### 构造函数
```python
DataDeduplicator()
```

创建一个新的数据去重处理器实例。

#### 主要方法

##### remove_duplicates()

基于列名进行去重操作。

```python
remove_duplicates(
    df: pd.DataFrame,
    key_columns: Union[str, List[str]],
    strategy: DeduplicationStrategy = DeduplicationStrategy.FIRST,
    keep_stats: bool = True
) -> pd.DataFrame
```

**参数:**
- `df`: 输入的 DataFrame
- `key_columns`: 用于去重的列名或列名列表
- `strategy`: 去重策略（FIRST/LAST/RANDOM）
- `keep_stats`: 是否保留统计信息

**返回:**
- 去重后的 DataFrame

**示例:**
```python
# 保留每个ID的首次记录
result = deduplicator.remove_duplicates(df, 'id')

# 保留每个ID-VALUE组合的最后记录
result = deduplicator.remove_duplicates(
    df,
    ['id', 'value'],
    strategy=DeduplicationStrategy.LAST
)
```

##### deduplicate_by_key()

基于自定义函数进行去重操作。

```python
deduplicate_by_key(
    df: pd.DataFrame,
    key_func: Callable[[pd.Series], str],
    strategy: DeduplicationStrategy = DeduplicationStrategy.FIRST,
    keep_stats: bool = True
) -> pd.DataFrame
```

**参数:**
- `df`: 输入的 DataFrame
- `key_func`: 自定义键生成函数
- `strategy`: 去重策略
- `keep_stats`: 是否保留统计信息

**示例:**
```python
def composite_key(row):
    return f"{row['category']}_{row['date'].strftime('%Y-%m')}"

# 按月份和类别去重
result = deduplicator.deduplicate_by_key(df, composite_key)
```

##### get_duplicate_stats()

获取重复数据统计信息。

```python
get_duplicate_stats(
    df: pd.DataFrame,
    key_columns: Union[str, List[str]]
) -> Dict[str, Any]
```

**返回:**
- 包含以下键的字典：
  - `total_records`: 总记录数
  - `unique_records`: 唯一记录数
  - `duplicate_records`: 重复记录数
  - `duplicate_rate`: 重复率
  - `duplicate_groups`: 重复组数
  - `top_duplicates`: 主要重复项

**示例:**
```python
stats = deduplicator.get_duplicate_stats(df, ['id'])
print(f"重复率: {stats['duplicate_rate']:.2%}")
print(f"重复记录数: {stats['duplicate_records']}")
```

### DeduplicationStrategy 枚举

```python
class DeduplicationStrategy(Enum):
    FIRST = "first"   # 保留首次出现的记录
    LAST = "last"     # 保留最后一次出现的记录
    RANDOM = "random" # 随机保留一条记录
```

## 实际应用场景

### 1. 用户行为数据去重

```python
# 去除用户在同一分钟内的重复行为记录
def minute_key(row):
    return f"{row['user_id']}_{row['timestamp'].strftime('%Y-%m-%d %H:%M')}"

cleaned_data = deduplicator.deduplicate_by_key(
    user_behavior_df,
    minute_key,
    strategy=DeduplicationStrategy.LAST
)
```

### 2. 股票分笔数据清洗

```python
# 按时间戳和价格去重，保留最后出现的记录
tick_data_cleaned = deduplicator.remove_duplicates(
    tick_data,
    ['time', 'price', 'stock_code'],
    strategy=DeduplicationStrategy.LAST
)
```

### 3. 日志数据处理

```python
# 去除相同错误类型的重复日志
error_stats = deduplicator.get_duplicate_stats(
    error_logs_df,
    ['error_type', 'error_message']
)

print(f"发现 {error_stats['duplicate_groups']} 组重复错误")
```

## 性能优化建议

### 1. 选择合适的键类型

**推荐（高性能）:**
```python
# 使用多字段组合
result = deduplicator.remove_duplicates(df, ['field1', 'field2'])
```

**谨慎使用（性能较低）:**
```python
# 复杂的自定义函数
def complex_key(row):
    # 包含复杂计算
    return heavy_calculation(row)

result = deduplicator.deduplicate_by_key(df, complex_key)
```

### 2. 大数据量处理

```python
# 对于大数据集，考虑分批处理
def batch_deduplicate(df, batch_size=100000):
    results = []
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        cleaned_batch = deduplicator.remove_duplicates(batch, ['id'])
        results.append(cleaned_batch)
    return pd.concat(results, ignore_index=True)
```

### 3. 内存优化

```python
# 处理完成后及时清理统计信息
result = deduplicator.remove_duplicates(df, ['id'], keep_stats=False)
```

## 错误处理

### 常见错误和解决方案

1. **列不存在错误**
   ```python
   # 错误：列名不存在
   deduplicator.remove_duplicates(df, ['nonexistent_column'])

   # 解决：检查列是否存在
   required_columns = ['id', 'value']
   available_columns = df.columns.tolist()
   missing_columns = [col for col in required_columns if col not in available_columns]

   if missing_columns:
       raise ValueError(f"缺少必需的列: {missing_columns}")
   ```

2. **键函数异常**
   ```python
   # 添加异常处理
   def safe_key_func(row):
       try:
           return f"{row['id']}_{row['value']}"
       except KeyError as e:
           print(f"缺少字段: {e}")
           return None

   # 过滤无效键
   result = deduplicator.deduplicate_by_key(df, safe_key_func)
   ```

## 统计信息分析

### 评估数据质量

```python
def analyze_data_quality(df, key_columns):
    stats = deduplicator.get_duplicate_stats(df, key_columns)

    print("=== 数据质量报告 ===")
    print(f"总记录数: {stats['total_records']:,}")
    print(f"唯一记录数: {stats['unique_records']:,}")
    print(f"重复记录数: {stats['duplicate_records']:,}")
    print(f"重复率: {stats['duplicate_rate']:.2%}")

    if stats['duplicate_rate'] > 0.5:
        print("⚠️  警告：重复率超过50%，建议检查数据源")
    elif stats['duplicate_rate'] > 0.1:
        print("ℹ️  注意：存在一定重复，建议清洗数据")
    else:
        print("✅ 数据重复率较低，质量良好")

    return stats

# 使用示例
quality_report = analyze_data_quality(df, ['user_id', 'action_date'])
```

### 重复模式分析

```python
def analyze_duplicate_patterns(df, key_column):
    stats = deduplicator.get_duplicate_stats(df, [key_column])

    if stats['top_duplicates']:
        print("\n=== 主要重复项 ===")
        for item in stats['top_duplicates'][:10]:  # 显示前10个
            print(f"{item['key']}: {item['count']} 次重复")

analyze_duplicate_patterns(user_logs_df, 'user_id')
```

## 最佳实践

### 1. 选择合适的去重策略
- **FIRST**: 适用于需要保留历史记录的场景
- **LAST**: 适用于需要保留最新状态的场景
- **RANDOM**: 适用于随机采样场景

### 2. 组合使用多种方法
```python
# 先按时间去重，再按ID去重
step1 = deduplicator.remove_duplicates(
    df,
    ['timestamp'],
    strategy=DeduplicationStrategy.LAST
)
final_result = deduplicator.remove_duplicates(
    step1,
    ['user_id'],
    strategy=DeduplicationStrategy.FIRST
)
```

### 3. 验证去重结果
```python
def validate_deduplication(original_df, deduped_df, key_columns):
    # 验证去重是否正确
    original_keys = original_df[key_columns].apply(
        lambda row: '_'.join(map(str, row)), axis=1
    )
    deduped_keys = deduped_df[key_columns].apply(
        lambda row: '_'.join(map(str, row)), axis=1
    )

    assert len(deduped_keys) == len(deduped_keys.unique()), "去重失败：仍有重复键"
    assert len(deduped_df) <= len(original_df), "去重错误：记录数增加"

    print("✅ 去重验证通过")

validate_deduplication(df, result, ['id', 'value'])
```

## 技术规格

- **支持的数据类型**: pandas DataFrame
- **内存使用**: 优化为线性复杂度
- **时间复杂度**: O(n log n) (主要由于排序)
- **支持的Python版本**: 3.8+
- **依赖库**: pandas, numpy

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基础的列去重和自定义函数去重
- 实现三种去重策略
- 添加统计信息功能
- 性能优化：大数据量处理 < 3秒

## 常见问题

**Q: 自定义函数去重为什么比较慢？**
A: 自定义函数需要逐行处理，无法利用向量化操作。建议优先使用多字段组合去重。

**Q: 如何处理包含NaN值的去重？**
A: NaN在pandas中被视为唯一值，因此包含NaN的行不会被去重。如需处理，建议先填充或删除NaN值。

**Q: 可以保持原始数据的顺序吗？**
A: FIRST策略会保持相对顺序，但LAST和RANDOM策略可能会改变顺序。如需保持顺序，建议在去重后重新排序。

---

如有问题或建议，请查看源码或联系开发团队。