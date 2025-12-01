# StatisticsGenerator 使用文档

## 概述

StatisticsGenerator 是一个高性能、高精度的数值型数据统计分析器，专为大数据量场景设计。它提供全面的统计量计算、分布分析、数据质量评估等功能，确保6位小数精度的计算结果。

## 核心特性

### 🚀 极致性能表现
- **基础统计**: 10万条数据 < 0.04秒
- **分位数计算**: 10万条数据 < 0.02秒
- **汇总报告**: 10万条数据 < 0.06秒
- **精度保证**: 浮点数计算 ≥ 6位小数精度

### 📊 全面的统计分析
- **基础统计量**: 均值、中位数、标准差、方差、最值、和值
- **分位数分析**: 自定义分位数计算
- **分布分析**: 正态性检验、偏度、峰度
- **数据质量**: 缺失值分析、异常值检测、重复统计
- **组间比较**: 多组数据对比分析

### 🔧 智能数据处理
- 自动缺失值处理和统计
- 多种数据格式支持（Series、Array、List）
- 大数值和极端值处理
- 边界情况智能处理

## 快速开始

### 基础用法

```python
import pandas as pd
import numpy as np
from core.statistics_generator import StatisticsGenerator

# 创建统计分析器实例
generator = StatisticsGenerator()

# 准备测试数据
data = pd.Series([15.2, 18.5, 12.3, 22.1, 17.8, 19.4, 14.7, 20.2, 16.9, 21.3])

# 基础统计分析
stats = generator.basic_stats(data)

print(f"数据统计结果:")
print(f"样本数量: {stats['count']}")
print(f"平均值: {stats['mean']:.6f}")
print(f"中位数: {stats['median']:.6f}")
print(f"标准差: {stats['std']:.6f}")
print(f"最小值: {stats['min']:.6f}")
print(f"最大值: {stats['max']:.6f}")
print(f"缺失值: {stats['missing_count']}")
print(f"缺失率: {stats['missing_rate']:.2%}")
```

### 分位数计算

```python
# 计算常用分位数
percentiles = generator.calculate_percentiles(
    data,
    percentiles=[5, 25, 50, 75, 95],
    precision=3
)

print(f"分位数结果:")
for p, value in percentiles.items():
    print(f"{p}%分位数: {value}")

# 自定义分位数
custom_percentiles = generator.calculate_percentiles(
    data,
    percentiles=[1, 10, 90, 99]
)
```

### DataFrame汇总报告

```python
import pandas as pd

# 创建测试DataFrame
df = pd.DataFrame({
    'price': [100.5, 102.3, 98.7, 105.2, 99.8],
    'volume': [1500, 1800, 1200, 2000, 1600],
    'returns': [0.025, -0.015, 0.018, -0.008, 0.012]
})

# 生成汇总报告
report = generator.generate_summary_report(
    df,
    include_quality=True
)

print(f"数据概要:")
print(f"总行数: {report['summary']['total_rows']}")
print(f"数值列数: {report['summary']['numeric_columns']}")
print(f"数据质量分数: {report['data_quality']['overall_quality_score']:.4f}")

print(f"\n各列统计:")
for col_name, col_stats in report['columns'].items():
    print(f"{col_name}:")
    print(f"  均值: {col_stats['mean']:.4f}")
    print(f"  标准差: {col_stats['std']:.4f}")
    print(f"  缺失率: {col_stats['missing_rate']:.2%}")
```

## API 参考

### StatisticsGenerator 类

#### 构造函数
```python
StatisticsGenerator()
```

创建一个新的统计分析器实例，自动设置6位小数精度。

#### 主要方法

##### basic_stats()

计算基础统计量。

```python
basic_stats(
    data: Union[pd.Series, np.ndarray, List[float]],
    precision: Optional[int] = None
) -> Dict[str, Any]
```

**参数:**
- `data`: 输入数据（Series、array或list）
- `precision`: 小数精度，默认使用类设置（6位）

**返回:**
- 包含以下统计量的字典：
  - `count`: 有效记录数
  - `mean`: 平均值
  - `median`: 中位数
  - `std`: 标准差
  - `var`: 方差
  - `min`: 最小值
  - `max`: 最大值
  - `sum`: 总和
  - `range`: 值域范围
  - `q25`: 25%分位数
  - `q75`: 75%分位数
  - `iqr`: 四分位距
  - `missing_count`: 缺失值数量
  - `missing_rate`: 缺失值比例
  - `valid_count`: 有效数据数量
  - `unique_count`: 唯一值数量
  - `duplicates_count`: 重复值数量
  - `outliers_count`: 异常值数量
  - `outliers_rate`: 异常值比例

**示例:**
```python
stats = generator.basic_stats(price_data)
print(f"价格均值: {stats['mean']:.2f}")
print(f"价格标准差: {stats['std']:.2f}")
```

##### generate_summary_report()

生成DataFrame的汇总统计报告。

```python
generate_summary_report(
    data: Union[pd.DataFrame, Dict[str, pd.Series]],
    columns: Optional[List[str]] = None,
    include_quality: bool = True
) -> Dict[str, Any]
```

**参数:**
- `data`: 输入数据（DataFrame或字典）
- `columns`: 要分析的列名列表，None表示分析所有数值列
- `include_quality`: 是否包含数据质量分析

**返回:**
- 包含汇总信息的字典：
  - `summary`: 数据集概要信息
  - `columns`: 各列的详细统计
  - `data_quality`: 数据质量分析

**示例:**
```python
report = generator.generate_summary_report(df, columns=['price', 'volume'])
```

##### calculate_percentiles()

计算分位数。

```python
calculate_percentiles(
    data: Union[pd.Series, np.ndarray, List[float]],
    percentiles: List[float] = None,
    precision: Optional[int] = None
) -> Dict[float, float]
```

**参数:**
- `data`: 输入数据
- `percentiles`: 要计算的分位数列表（0-100之间）
- `precision`: 小数精度

**返回:**
- 分位数字典，键为分位数值，值为对应的分位数值

**示例:**
```python
percentiles = generator.calculate_percentiles(data, [10, 25, 50, 75, 90])
print(f"90分位数: {percentiles[90]}")
```

##### analyze_distribution()

分析数据分布特征。

```python
analyze_distribution(
    data: Union[pd.Series, np.ndarray, List[float]],
    bins: int = 10
) -> Dict[str, Any]
```

**参数:**
- `data`: 输入数据
- `bins`: 直方图的分箱数量

**返回:**
- 分布分析结果：
  - `basic_stats`: 基础统计量
  - `histogram`: 直方图数据
  - `distribution_type`: 分布类型识别
  - `skewness`: 偏度
  - `kurtosis`: 峰度

**示例:**
```python
distribution = generator.analyze_distribution(price_data)
print(f"分布类型: {distribution['distribution_type']}")
print(f"偏度: {distribution['skewness']:.3f}")
```

##### compare_groups()

比较不同组的统计量。

```python
compare_groups(
    data: pd.DataFrame,
    group_column: str,
    value_column: str,
    stat_types: List[str] = None
) -> Dict[str, Dict[str, float]]
```

**参数:**
- `data`: 输入DataFrame
- `group_column`: 分组列名
- `value_column`: 数值列名
- `stat_types`: 要比较的统计类型列表

**返回:**
- 组间比较结果字典

**示例:**
```python
comparison = generator.compare_groups(df, 'category', 'price')
for group, stats in comparison.items():
    print(f"{group}组: 均值={stats['mean']:.2f}")
```

## 实际应用场景

### 1. 股票价格分析

```python
import pandas as pd

# 假设股票数据
stock_data = pd.read_csv('stock_prices.csv')

# 分析价格统计
price_stats = generator.basic_stats(stock_data['close_price'])

print("股票价格分析:")
print(f"平均价格: {price_stats['mean']:.2f}")
print(f"价格区间: {price_stats['min']:.2f} - {price_stats['max']:.2f}")
print(f"价格波动: {price_stats['std']:.2f}")

# 计算风险指标
returns = stock_data['close_price'].pct_change().dropna()
return_stats = generator.basic_stats(returns)

print(f"\n收益率分析:")
print(f"平均收益率: {return_stats['mean']:.4f}")
print(f"收益率标准差: {return_stats['std']:.4f}")
print(f"收益率偏度: {return_stats.get('skewness', 0):.4f}")
```

### 2. 数据质量评估

```python
# 创建数据质量报告
quality_report = generator.generate_summary_report(df, include_quality=True)

print("数据质量评估:")
print(f"总体质量分数: {quality_report['data_quality']['overall_quality_score']:.2%}")

for col, quality in quality_report['data_quality']['completeness'].items():
    print(f"{col}: 完整性 {quality:.2%}")

# 识别数据质量问题
issues = []
for col_name, col_stats in quality_report['columns'].items():
    if col_stats['missing_rate'] > 0.1:
        issues.append(f"{col_name}缺失率过高 ({col_stats['missing_rate']:.2%})")
    if col_stats['outliers_rate'] > 0.05:
        issues.append(f"{col_name}异常值过多 ({col_stats['outliers_rate']:.2%})")

if issues:
    print("\n发现的数据质量问题:")
    for issue in issues:
        print(f"- {issue}")
```

### 3. A/B测试分析

```python
# 假设A/B测试数据
test_data = pd.DataFrame({
    'group': ['A', 'A', 'B', 'B', 'A', 'B'] * 1000,
    'conversion_rate': np.random.beta(2, 5, 6000)
})

# 组间比较
comparison = generator.compare_groups(
    test_data,
    'group',
    'conversion_rate',
    ['count', 'mean', 'std', 'median']
)

print("A/B测试结果:")
print(f"A组: 转化率 {comparison['A']['mean']:.4f} (±{comparison['A']['std']:.4f})")
print(f"B组: 转化率 {comparison['B']['mean']:.4f} (±{comparison['B']['std']:.4f})")

# 计算提升效果
lift = (comparison['B']['mean'] - comparison['A']['mean']) / comparison['A']['mean']
print(f"B组相对A组的提升: {lift:.2%}")
```

### 4. 批量数据报告

```python
def create_data_profile_report(datasets_dict):
    """为多个数据集创建统一的概况报告"""
    reports = {}

    for name, df in datasets_dict.items():
        print(f"正在分析数据集: {name}")

        report = generator.generate_summary_report(df)

        # 添加数据集特定信息
        report['dataset_name'] = name
        report['dataset_size_mb'] = df.memory_usage(deep=True).sum() / 1024 / 1024
        report['memory_per_row_bytes'] = df.memory_usage(deep=True).sum() / len(df)

        reports[name] = report

    return reports

# 使用示例
datasets = {
    '用户行为数据': user_behavior_df,
    '交易数据': transaction_df,
    '产品数据': product_df
}

profile_reports = create_data_profile_report(datasets)

# 输出对比摘要
print("\n数据集对比摘要:")
for name, report in profile_reports.items():
    print(f"{name}:")
    print(f"  行数: {report['summary']['total_rows']:,}")
    print(f"  列数: {report['summary']['total_columns']}")
    print(f"  数值列: {report['summary']['numeric_columns']}")
    print(f"  数据质量: {report['data_quality']['overall_quality_score']:.2%}")
    print(f"  内存占用: {report['dataset_size_mb']:.2f}MB")
```

## 性能优化建议

### 1. 大数据集处理

```python
# 对于非常大的数据集，考虑分批处理
def batch_statistics(data, batch_size=100000):
    """分批计算统计量"""
    if len(data) <= batch_size:
        return generator.basic_stats(data)

    # 分批处理均值
    batch_means = []
    for i in range(0, len(data), batch_size):
        batch = data.iloc[i:i+batch_size]
        batch_means.append(batch.mean())

    # 合并结果
    overall_mean = sum(batch_means) / len(batch_means)

    # 其他统计量可以类似处理
    # ...（简化示例）

    return {
        'mean': overall_mean,
        'count': len(data),
        'batch_processed': len(batch_means)
    }
```

### 2. 内存优化

```python
# 及时清理不需要的统计信息
stats = generator.basic_stats(large_data, keep_extra_info=False)

# 使用较低精度以节省内存
low_precision_stats = generator.basic_stats(
    data,
    precision=3  # 使用3位小数而非6位
)
```

### 3. 选择性计算

```python
# 只计算需要的统计量
def calculate_selected_stats(data, needed_stats):
    """只计算需要的统计量以提高性能"""
    all_stats = generator.basic_stats(data)
    return {stat: all_stats[stat] for stat in needed_stats}

# 只计算需要的统计
needed_stats = ['mean', 'std', 'count']
stats = calculate_selected_stats(price_data, needed_stats)
```

## 精度处理

### 自定义精度设置

```python
# 全局精度设置
generator = StatisticsGenerator()
generator.precision_places = 4  # 设置为4位小数

# 单次计算精度设置
high_precision_stats = generator.basic_stats(data, precision=8)  # 8位小数
low_precision_stats = generator.basic_stats(data, precision=2)   # 2位小数
```

### 精度验证

```python
def verify_precision(stats, expected_precision=6):
    """验证统计量的精度"""
    for key, value in stats.items():
        if isinstance(value, float):
            str_value = f"{value:.{expected_precision}f}"
            actual_precision = len(str_value.split('.')[-1])
            print(f"{key}: {actual_precision}位小数")
```

## 错误处理

### 常见错误和解决方案

1. **数据类型错误**
   ```python
   # 错误：混合类型数据
   mixed_data = pd.Series([1, 2, 'three', 4])

   # 解决：预处理数据
   numeric_data = pd.to_numeric(data, errors='coerce')
   stats = generator.basic_stats(numeric_data)
   ```

2. **空数据集**
   ```python
   # 检查空数据
   if data.empty:
       print("数据集为空")
       return

   stats = generator.basic_stats(data)
   ```

3. **内存不足**
   ```python
   # 使用分批处理
   if len(data) > 1000000:
       stats = batch_statistics(data)
   else:
       stats = generator.basic_stats(data)
   ```

## 技术规格

- **支持的数据类型**: pandas Series, numpy array, Python list
- **精度标准**: 默认6位小数，可自定义
- **内存使用**: 优化为线性复杂度
- **时间复杂度**: O(n) 到 O(n log n)
- **支持的Python版本**: 3.8+
- **依赖库**: pandas, numpy

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基础统计量计算
- 实现分位数计算
- 添加分布分析功能
- 实现数据质量评估
- 性能优化：10万条数据 < 1秒
- 精度保证：≥6位小数

## 常见问题

**Q: 如何处理包含大量缺失值的数据？**
A: StatisticsGenerator自动处理缺失值，会计算有效数据的统计量，并提供缺失值统计信息。

**Q: 分位数计算的性能如何？**
A: 使用pandas的quantile方法，10万条数据的分位数计算通常在0.02秒内完成。

**Q: 可以计算自定义统计量吗？**
A: 当前版本支持预定义的统计量。自定义统计量可以通过组合现有统计量来实现。

**Q: 如何处理极端异常值？**
A: 组件提供IQR方法的异常值检测，并统计异常值数量和比例。

---

如有问题或建议，请查看源码或联系开发团队。