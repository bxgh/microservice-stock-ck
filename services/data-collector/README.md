# AKShare 数据收集器项目

## 📋 项目概述

本项目在虚拟环境中测试并配置了AKShare库，确定了除东方财富数据源外的可用接口，并提供了完整的文档和使用示例。

## 📁 项目文件结构

```
services/data-collector/
├── venv/                           # Python虚拟环境
├── AKSHARE_AVAILABLE_APIS.md       # 完整的API文档
├── akshare_config.py              # 配置文件和管理类
├── akshare_example.py             # 基础使用示例
├── akshare_solutions.py           # 问题解决方案
├── available_apis_summary.py      # 可用API总结
├── debug_akshare.py               # 调试脚本
├── simple_api_test.py             # 简单API测试
├── test_alternative_sources.py    # 替代数据源测试
├── extended_api_test.py           # 扩展API测试
└── README.md                      # 项目说明文件
```

## 🚀 快速开始

### 1. 激活虚拟环境
```bash
cd /home/bxgh/microservice-stock/services/data-collector
source venv/bin/activate
```

### 2. 查看可用API
```python
from akshare_config import list_available_apis
list_available_apis()
```

### 3. 使用示例
```python
from akshare_config import get_trading_dates, get_index_constituents

# 获取交易日期
dates = get_trading_dates()
print(f"总交易日: {len(dates)}")

# 获取沪深300成分股
stocks = get_index_constituents("000300")
print(f"沪深300成分股: {len(stocks)} 只")
```

## ✅ 可用数据源

### 📅 交易日历类 (最推荐)
- `tool_trade_date_hist_sina()` - 交易日期查询 (8555条记录)

### 💰 基金ETF类
- `fund_etf_spot_ths()` - ETF实时数据 (1380条记录)
- `fund_etf_hist_sina()` - ETF历史数据 (5039条记录)
- `fund_scale_open_sina()` - 开放式基金规模 (6024条记录)

### 📈 指数成分股类
- `index_stock_cons("000300")` - 沪深300成分股
- `index_stock_cons("000016")` - 上证50成分股
- `index_stock_cons("000905")` - 中证500成分股

### 💱 外汇汇率类
- `currency_boc_sina()` - 中国银行汇率 (180条记录)

### 📊 概念板块类
- `stock_board_concept_name_ths()` - 概念板块 (374条)
- `stock_board_concept_index_ths()` - 概念指数 (1248条)

### 🏦 债券类
- `bond_zh_cov_info_ths()` - 债券信息 (896条记录)
- `bond_cb_profile_sina()` - 可转债信息 (25条记录)

## ❌ 不可用数据源

- **东方财富数据源** - SSL连接问题
- **腾讯财经数据源** - 未发现API
- **宏观经济数据源** - 大部分不可用

## 📖 详细文档

1. **[AKSHARE_AVAILABLE_APIS.md](./AKSHARE_AVAILABLE_APIS.md)**
   - 完整的API接口文档
   - 包含详细的参数、返回值和使用示例

2. **[akshare_config.py](./akshare_config.py)**
   - 配置文件和管理类
   - 提供安全的API调用机制
   - 包含重试和错误处理

3. **[akshare_example.py](./akshare_example.py)**
   - 基础使用示例
   - 实用工具函数

## 🛠️ 环境配置

### Python版本
- Python 3.12.3

### AKShare版本
- 1.17.85 (使用清华镜像源安装)

### 依赖包
- pandas, requests, beautifulsoup4, lxml等

### 安装命令
```bash
pip install akshare -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 💡 推荐使用场景

### 1. 交易日历工具
```python
from akshare_config import get_trading_dates

# 构建交易日历
dates = get_trading_dates()
```

### 2. 指数成分股筛选
```python
from akshare_config import get_index_constituents

# 获取股票池
stocks = get_index_constituents("000300")  # 沪深300
```

### 3. ETF基金分析
```python
from akshare_config import get_etf_data

# 获取ETF数据
spot_data, hist_data = get_etf_data()
```

### 4. 概念板块监控
```python
from akshare_config import AKShareManager

manager = AKShareManager()
concepts = manager.safe_api_call('stock_board_concept_name_ths')
```

## ⚠️ 注意事项

1. **网络限制**: 东方财富数据源不可用，建议使用新浪财经和同花顺
2. **请求频率**: 建议在API调用间添加0.5秒延时
3. **错误处理**: 使用配置文件中的安全API调用方法
4. **重试机制**: 自动实现3次重试，指数退避延迟

## 📊 性能统计

| API类型 | 平均响应时间 | 数据量 | 稳定性 |
|---------|-------------|--------|--------|
| 交易日历 | ~0.25s | 8555条 | ⭐⭐⭐⭐⭐ |
| 指数成分股 | ~0.5s | 50-500条 | ⭐⭐⭐⭐⭐ |
| ETF数据 | ~0.8s | 1380条 | ⭐⭐⭐⭐ |
| 外汇汇率 | ~0.9s | 180条 | ⭐⭐⭐⭐ |

## 🎯 结论

虽然东方财富数据源不可用，但**新浪财经 + 同花顺**的组合提供了丰富的数据，完全足够开发：
- 交易日历工具
- 基金ETF分析系统
- 指数成分股筛选器
- 概念板块监控应用
- 汇率查询工具

## 📞 技术支持

如遇问题：
1. 检查网络连接
2. 使用配置文件中的安全调用方法
3. 参考完整文档
4. 实现自定义错误处理

---

**项目创建时间**: 2025-11-17
**最后更新时间**: 2025-11-17
**测试环境**: Ubuntu Linux + Python 3.12.3