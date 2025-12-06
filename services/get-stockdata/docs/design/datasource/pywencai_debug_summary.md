# pywencai调试总结

## 环境要求
- Python 3.11+
- Node.js v16+ (用于执行JS代码)
- 已安装pywencai 0.0.1

## 安装命令
```bash
pip install pywencai
```

## 调试结果

### ✅ 成功功能
1. **股票基本信息查询** - 可以获取单个股票的详细信息
2. **股票列表查询** - 支持涨幅榜、成交量排行等
3. **概念股查询** - 可以按概念筛选股票
4. **指数查询** - 支持各类指数数据获取
5. **自定义wencai模块** - 项目的baseWencai.py模块工作正常

### 📊 返回数据格式
- **单股票查询**: 返回字典格式，包含多个DataFrame
  - `kline2`: 股票基本信息
  - `impressionLabel`: 概念标签
  - `重要事件`: 重要事件数据
  - `财务数据`: 财务报表数据
  - 等等...

- **股票列表查询**: 直接返回DataFrame格式
  - 包含股票代码、名称、价格等基本信息
  - 支持perpage参数控制数量

### 🔧 使用示例

#### 1. 获取股票基本信息
```python
import pywencai

# 查询平安银行
result = pywencai.get(query='平安银行')
# 返回字典格式，访问result['kline2']获取基本信息
```

#### 2. 获取股票列表
```python
# 获取涨幅榜前10名
result = pywencai.get(query='涨幅榜', perpage=10)
# 返回DataFrame格式
```

#### 3. 使用项目中的模块
```python
from Common import baseWencai as wenCai

result = wenCai.wencai('平安银行', 'stock')
```

### ⚠️ 注意事项
1. **编码问题**: Windows控制台可能出现中文乱码，建议使用UTF-8环境
2. **Node.js警告**: 会有punycode模块弃用警告，不影响功能
3. **网络要求**: 需要稳定的网络连接访问同花顺接口
4. **频率限制**: 避免过于频繁的请求，项目中的重试机制很好

### 🚀 主要文件位置
- `Common/baseWencai.py` - 核心封装模块
- `TaskFunction/jqka10/scrap_stock.py` - 股票数据抓取
- `TaskFunction/jqka10/scrap_zhishu.py` - 指数数据抓取
- `debug_pywencai.py` - 调试脚本
- `pywencai_usage_example.py` - 使用示例

### ✨ 结论
pywencai已经成功配置并可以正常使用，所有核心功能都工作正常。项目的股票数据获取系统可以正常运行。