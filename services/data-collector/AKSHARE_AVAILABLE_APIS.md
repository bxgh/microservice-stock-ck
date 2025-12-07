# AKShare 可用接口文档

## 📋 项目信息
- **项目名称**: AKShare 数据源测试
- **测试时间**: 2025-11-17
- **AKShare版本**: 1.17.85
- **Python版本**: 3.12.3
- **测试环境**: Ubuntu Linux

---

## 🎯 核心结论

### ✅ 可用数据源
1. **新浪财经数据源** - ⭐⭐⭐⭐⭐ (最稳定)
2. **同花顺数据源** - ⭐⭐⭐⭐ (部分可用)
3. **指数成分股数据源** - ⭐⭐⭐⭐⭐ (完全可用)

### ❌ 不可用数据源
1. **东方财富数据源** - SSL连接问题
2. **腾讯财经数据源** - 未发现API
3. **宏观经济数据源** - 大部分不可用

---

## 📊 详细可用接口列表

### 1. 📅 交易日历类 (最推荐)

#### `ak.tool_trade_date_hist_sina()`
- **功能**: 获取中国股市所有交易日期
- **数据源**: 新浪财经
- **数据量**: 8555条记录
- **时间范围**: 1990-12-19 至 2025-12-31
- **状态**: ✅ 100%可用
- **响应时间**: ~0.25秒
- **返回格式**: DataFrame
```python
# 使用示例
import akshare as ak
dates = ak.tool_trade_date_hist_sina()
print(f"总交易日: {len(dates)}")
print(f"最早: {dates.iloc[0]['trade_date']}")
print(f"最近: {dates.iloc[-1]['trade_date']}")
```

---

### 2. 💰 基金ETF类

#### `ak.fund_etf_spot_ths()`
- **功能**: 获取ETF实时数据
- **数据源**: 同花顺
- **数据量**: 1380条记录
- **状态**: ✅ 可用
- **响应时间**: ~0.82秒
- **返回格式**: DataFrame
- **字段**: 序号、基金代码、基金名称等

#### `ak.fund_etf_category_sina()`
- **功能**: 获取ETF分类信息
- **数据源**: 新浪财经
- **数据量**: 361条记录
- **状态**: ✅ 可用
- **响应时间**: ~1.61秒
- **返回格式**: DataFrame
- **字段**: 代码、名称、最新价、涨跌额、涨跌幅

#### `ak.fund_etf_hist_sina()`
- **功能**: 获取ETF历史数据
- **数据源**: 新浪财经
- **数据量**: 5039条记录
- **状态**: ✅ 可用
- **响应时间**: ~0.94秒
- **返回格式**: DataFrame
- **字段**: date, prevclose, open, high, low等

#### `ak.fund_scale_open_sina()`
- **功能**: 获取开放式基金规模数据
- **数据源**: 新浪财经
- **数据量**: 6024条记录
- **状态**: ✅ 可用
- **响应时间**: ~21.87秒
- **返回格式**: DataFrame
- **字段**: 序号、基金代码、基金简称、单位净值等

#### `ak.fund_scale_close_sina()`
- **功能**: 获取封闭式基金规模数据
- **数据源**: 新浪财经
- **数据量**: 177条记录
- **状态**: ✅ 可用
- **响应时间**: ~1.89秒
- **返回格式**: DataFrame

---

### 3. 📈 指数成分股类 (强烈推荐)

#### `ak.index_stock_cons(symbol)`
- **功能**: 获取指定指数的成分股信息
- **数据源**: 多数据源
- **状态**: ✅ 主要指数完全可用
- **响应时间**: ~0.5秒
- **支持指数**:
  - `"000300"` - 沪深300 (300只股票)
  - `"000016"` - 上证50 (50只股票)
  - `"000905"` - 中证500 (500只股票)
- **返回格式**: DataFrame
- **字段**: 品种代码、品种名称、纳入日期等

```python
# 使用示例
import akshare as ak

# 获取沪深300成分股
hs300_stocks = ak.index_stock_cons("000300")
print(f"沪深300成分股数量: {len(hs300_stocks)}")

# 获取上证50成分股
sz50_stocks = ak.index_stock_cons("000016")
print(f"上证50成分股数量: {len(sz50_stocks)}")
```

---

### 4. 💱 外汇汇率类

#### `ak.currency_boc_sina()`
- **功能**: 获取中国银行外汇汇率
- **数据源**: 新浪财经
- **数据量**: 180条记录
- **状态**: ✅ 可用
- **响应时间**: ~0.92秒
- **返回格式**: DataFrame
- **字段**: 日期、中行汇买价、中行钞买价、中行钞卖价/汇卖价、央行中间价

---

### 5. 🏦 债券类

#### `ak.bond_cb_profile_sina()`
- **功能**: 获取可转债基本信息
- **数据源**: 新浪财经
- **数据量**: 25条记录
- **状态**: ✅ 可用
- **响应时间**: ~0.48秒
- **返回格式**: DataFrame
- **字段**: item, value

#### `ak.bond_cb_summary_sina()`
- **功能**: 获取可转债汇总信息
- **数据源**: 新浪财经
- **数据量**: 15条记录
- **状态**: ✅ 可用
- **响应时间**: ~0.63秒
- **返回格式**: DataFrame

#### `ak.bond_zh_cov_info_ths()`
- **功能**: 获取债券可转债信息
- **数据源**: 同花顺
- **数据量**: 896条记录
- **状态**: ✅ 可用
- **响应时间**: ~0.62秒
- **返回格式**: DataFrame
- **字段**: 债券代码、债券简称、申购日期等

---

### 6. 📊 概念板块类

#### `ak.stock_board_concept_name_ths()`
- **功能**: 获取概念板块名称列表
- **数据源**: 同花顺
- **数据量**: 374条记录
- **状态**: ✅ 可用
- **响应时间**: <0.01秒
- **返回格式**: DataFrame
- **字段**: name, code

#### `ak.stock_board_concept_index_ths()`
- **功能**: 获取概念板块指数数据
- **数据源**: 同花顺
- **数据量**: 1248条记录
- **状态**: ✅ 可用
- **响应时间**: ~9.73秒
- **返回格式**: DataFrame
- **字段**: 日期、开盘价、最高价等

#### `ak.stock_board_concept_info_ths()`
- **功能**: 获取概念板块基本信息
- **数据源**: 同花顺
- **数据量**: 10条记录
- **状态**: ✅ 可用
- **响应时间**: ~0.22秒
- **返回格式**: DataFrame

---

## 🛠️ 环境配置

### 虚拟环境设置
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装AKShare (使用清华镜像源)
pip install akshare -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 基本配置
```python
import akshare as ak
import pandas as pd
from datetime import datetime

print(f"AKShare版本: {ak.__version__}")
print(f"Pandas版本: {pd.__version__}")
```

---

## 📝 使用示例

### 示例1: 交易日历应用
```python
def get_trading_dates():
    """获取所有交易日期"""
    dates = ak.tool_trade_date_hist_sina()
    return dates

def is_trading_day(date_str):
    """检查指定日期是否为交易日"""
    dates = ak.tool_trade_date_hist_sina()
    return date_str in dates['trade_date'].values

def get_recent_trading_days(days=10):
    """获取最近N个交易日"""
    dates = ak.tool_trade_date_hist_sina()
    return dates.tail(days)
```

### 示例2: 指数成分股应用
```python
def get_index_constituents(index_code="000300"):
    """获取指数成分股
    Args:
        index_code: 指数代码 (000300=沪深300, 000016=上证50)
    """
    try:
        stocks = ak.index_stock_cons(index_code)
        return stocks
    except Exception as e:
        print(f"获取指数成分股失败: {e}")
        return None

# 获取沪深300成分股
hs300_stocks = get_index_constituents("000300")
if hs300_stocks is not None:
    print(f"沪深300成分股数量: {len(hs300_stocks)}")
```

### 示例3: ETF数据应用
```python
def get_etf_data():
    """获取ETF相关数据"""
    try:
        # 获取ETF实时数据
        etf_spot = ak.fund_etf_spot_ths()
        print(f"ETF总数: {len(etf_spot)}")

        # 获取ETF历史数据
        etf_hist = ak.fund_etf_hist_sina()
        print(f"ETF历史数据: {len(etf_hist)} 条记录")

        return etf_spot, etf_hist
    except Exception as e:
        print(f"获取ETF数据失败: {e}")
        return None, None
```

---

## ⚠️ 注意事项和限制

### 网络限制
- **东方财富数据源**: SSL连接问题，暂时不可用
- **建议**: 优先使用新浪财经和同花顺数据源

### 调用频率
- **建议**: 在API调用间添加适当延时
- **推荐**: `time.sleep(0.5)` 避免请求过快

### 错误处理
```python
import time
import akshare as ak

def safe_api_call(api_func, max_retries=3, delay=1):
    """安全的API调用"""
    for attempt in range(max_retries):
        try:
            result = api_func()
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"第{attempt + 1}次尝试失败，{delay}秒后重试...")
                time.sleep(delay)
                delay *= 2  # 指数退避
            else:
                print(f"API调用失败: {e}")
                return None
```

---

## 🚀 推荐应用场景

### 1. 交易日历工具
- 使用 `tool_trade_date_hist_sina()` 构建完整的交易日历
- 支持交易日检查、节假日判断等功能

### 2. 指数成分股筛选器
- 基于指数成分股构建股票池
- 支持沪深300、上证50、中证500等主要指数

### 3. 基金ETF分析系统
- 实时ETF数据监控
- 历史数据分析
- 基金规模统计

### 4. 概念板块监控
- 跟踪概念板块表现
- 板块成分股分析

### 5. 汇率查询工具
- 实时汇率查询
- 历史汇率分析

---

## 📈 性能统计

| API名称 | 响应时间 | 数据量 | 稳定性 |
|---------|---------|--------|--------|
| tool_trade_date_hist_sina | ~0.25s | 8555条 | ⭐⭐⭐⭐⭐ |
| index_stock_cons | ~0.5s | 300-500条 | ⭐⭐⭐⭐⭐ |
| fund_etf_spot_ths | ~0.82s | 1380条 | ⭐⭐⭐⭐ |
| currency_boc_sina | ~0.92s | 180条 | ⭐⭐⭐⭐ |
| bond_zh_cov_info_ths | ~0.62s | 896条 | ⭐⭐⭐⭐ |
| fund_etf_hist_sina | ~0.94s | 5039条 | ⭐⭐⭐⭐ |

---

## 🔗 相关资源

- [AKShare官方文档](https://akshare.akfamily.xyz/)
- [Python虚拟环境指南](https://docs.python.org/3/library/venv.html)
- [Pandas数据处理文档](https://pandas.pydata.org/docs/)

---

## 📞 技术支持

如遇到问题，建议：
1. 检查网络连接
2. 更新AKShare版本
3. 使用重试机制
4. 查看官方文档

---

**文档更新时间**: 2025-11-17
**文档版本**: v1.0