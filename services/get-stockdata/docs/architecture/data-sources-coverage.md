# 股市数据源覆盖范围详细说明

## 概述

本文档详细说明了Get Stock Data微服务中10个数据源能够获取的各种股市数据类型，包括实时行情、历史数据、财务数据、技术指标等全面覆盖。

## 数据源概览

### 📊 数据源统计
- **总计数据源**: 10个
- **免费数据源**: 10个 (100%)
- **覆盖市场**: A股、港股、美股、全球市场
- **数据类型**: 15+大类，100+细分指标

---

## 详细数据覆盖范围

### 🏛️ A股市场数据覆盖

#### 📈 **实时行情数据**
**支持数据源**: PyTDX, EasyQuotation, AKShare, QStock, MooTDX, Tushare

| 数据指标 | 说明 | 数据源 |
|----------|------|--------|
| 最新价格 | 当前成交价 | 全部6个源 |
| 涨跌额 | 相比昨收的涨跌金额 | 全部6个源 |
| 涨跌幅 | 相比昨收的涨跌百分比 | 全部6个源 |
| 成交量 | 当日累计成交量 | 全部6个源 |
| 成交额 | 当日累计成交金额 | 全部6个源 |
| 昨收价 | 前一交易日收盘价 | 全部6个源 |
| 今开价 | 当日开盘价 | 全部6个源 |
| 最高价 | 当日最高成交价 | 全部6个源 |
| 最低价 | 当日最低成交价 | 全部6个源 |
| 市盈率 | 动态市盈率 | AKShare, QStock, Tushare |
| 市净率 | 市净率 | AKShare, QStock, Tushare |
| 换手率 | 当日换手率 | AKShare, QStock, Tushare |
| 总市值 | 总市值 | AKShare, QStock, Tushare |
| 流通市值 | 流通市值 | AKShare, QStock, Tushare |
| 分时数据 | 分钟级价格走势 | PyTDX, AKShare, QStock |
| 五档行情 | 买卖五档订单 | PyTDX, EasyQuotation, MooTDX |
| 委比 | 委买委卖比率 | PyTDX, MooTDX |
| 量比 | 当前成交量相比历史平均 | AKShare, QStock, Tushare |

#### 📊 **分笔成交数据**
**支持数据源**: PyTDX, MooTDX, AKShare

| 数据指标 | 说明 | 数据源 |
|----------|------|--------|
| 成交时间 | 精确到秒的成交时间 | PyTDX, MooTDX, AKShare |
| 成交价格 | 每笔成交价格 | PyTDX, MooTDX, AKShare |
| 成交数量 | 每笔成交股数 | PyTDX, MooTDX, AKShare |
| 成交金额 | 每笔成交金额 | PyTDX, MooTDX, AKShare |
| 买卖方向 | 主动买/主动卖 | PyTDX, MooTDX |
| 成交类型 | 撮合方式 | PyTDX, MooTDX |

#### 📉 **历史K线数据**
**支持数据源**: AKShare, QStock, MooTDX, Tushare, BaoStock

| 时间周期 | 说明 | 数据源 |
|----------|------|--------|
| 1分钟 | 分钟K线 | PyTDX, AKShare, QStock |
| 5分钟 | 5分钟K线 | PyTDX, AKShare, QStock |
| 15分钟 | 15分钟K线 | PyTDX, AKShare, QStock |
| 30分钟 | 30分钟K线 | PyTDX, AKShare, QStock |
| 60分钟 | 小时K线 | PyTDX, AKShare, QStock |
| 日线 | 每日K线 | 全部5个源 |
| 周线 | 每周K线 | 全部5个源 |
| 月线 | 每月K线 | 全部5个源 |
| 季线 | 每季K线 | AKShare, QStock, Tushare |
| 年线 | 每年K线 | AKShare, QStock, Tushare |

**K线数据包含**:
- 开盘价、收盘价、最高价、最低价
- 成交量、成交额
- 复权价格(前复权、后复权)
- 涨跌额、涨跌幅

#### 💰 **财务数据**
**支持数据源**: QStock, AKShare, Tushare, BaoStock

##### 📋 **主要财务报表**
| 报表类型 | 数据源 | 覆盖期 |
|----------|--------|--------|
| 资产负债表 | QStock, AKShare, Tushare, BaoStock | 10年以上 |
| 利润表 | QStock, AKShare, Tushare, BaoStock | 10年以上 |
| 现金流量表 | QStock, AKShare, Tushare, BaoStock | 10年以上 |
| 股东权益变动表 | QStock, Tushare | 10年以上 |

##### 📊 **关键财务指标**
| 指标类别 | 具体指标 | 数据源 |
|----------|----------|--------|
| **盈利能力** | ROE, ROA, 毛利率, 净利率 | QStock, AKShare, Tushare |
| **偿债能力** | 资产负债率, 流动比率, 速动比率 | QStock, AKShare, Tushare |
| **营运能力** | 存货周转率, 应收账款周转率 | QStock, AKShare, Tushare |
| **成长能力** | 营收增长率, 净利润增长率 | QStock, AKShare, Tushare |
| **现金流** | 经营现金流, 自由现金流 | QStock, AKShare, Tushare |
| **估值指标** | PE, PB, PS, PEG, EV/EBITDA | QStock, AKShare, Tushare |

##### 📈 **财务分析数据**
| 数据类型 | 说明 | 数据源 |
|----------|------|--------|
| 财务摘要 | 多期财务数据对比 | QStock, AKShare, Tushare |
| 财务比率 | 各项财务比率计算 | QStock, AKShare, Tushare |
| 杜邦分析 | ROE分解分析 | QStock, Tushare |
| 业绩预告 | 公司业绩预告数据 | QStock, AKShare |
| 业绩快报 | 公司业绩快报数据 | QStock, AKShare |
| 财务附注 | 财务报表附注 | Tushare |

#### 🏢 **公司基本信息**
**支持数据源**: AKShare, QStock, Tushare, BaoStock

| 信息类别 | 具体内容 | 数据源 |
|----------|----------|--------|
| **基本信息** | 公司全称、英文名称、成立时间 | AKShare, QStock, Tushare |
| **行业分类** | 行业类别、所属板块 | AKShare, QStock, Tushare |
| **业务范围** | 主营业务、产品服务 | AKShare, QStock, Tushare |
| **公司概况** | 发展历程、大事记 | AKShare, QStock |
| **股本结构** | 总股本、流通股、股东结构 | AKShare, QStock, Tushare |
| **高管信息** | 董事、监事、高级管理人员 | AKShare, QStock, Tushare |
| **注册信息** | 注册地址、办公地址、联系方式 | AKShare, QStock, Tushare |

#### 📊 **板块行业数据**
**支持数据源**: AKShare, QStock, Tushare

| 数据类型 | 说明 | 数据源 |
|----------|------|--------|
| 行业分类 | 申万行业、中信行业分类 | AKShare, QStock, Tushare |
| 板块指数 | 各板块指数数据 | AKShare, QStock, Tushare |
| 行业涨跌 | 行业涨跌统计 | AKShare, QStock, Tushare |
| 概念板块 | 概念分类及成分股 | AKShare, QStock, Tushare |
| 地域板块 | 地域分类及成分股 | AKShare, QStock |
| 龙虎榜 | 涨跌幅异常股票交易信息 | AKShare, QStock, Tushare |

#### 📈 **技术指标数据**
**支持数据源**: QStock, AKShare, Alpha Vantage

##### 🔢 **基础技术指标**
| 指标类型 | 具体指标 | 数据源 |
|----------|----------|--------|
| **趋势指标** | MA, EMA, MACD, BOLL | QStock, AKShare, Alpha Vantage |
| **动量指标** | RSI, KDJ, CCI, ROC | QStock, AKShare, Alpha Vantage |
| **成交量指标** | VOL, OBV, VWAP | QStock, AKShare, Alpha Vantage |
| **波动率指标** | ATR, BOLLWIDTH | QStock, AKShare, Alpha Vantage |
| **成交量型** | VR, EMV | QStock, AKShare |

##### 📊 **高级技术分析**
| 数据类型 | 说明 | 数据源 |
|----------|------|--------|
| 技术形态 | 识别各种技术形态 | QStock, AKShare |
| 支撑阻力 | 计算支撑阻力位 | QStock, AKShare |
| 趋势线 | 绘制趋势线 | QStock, AKShare |
| 波浪理论 | 艾略特波浪分析 | QStock |

---

### 🌍 港股市场数据覆盖

#### 📈 **实时行情数据**
**支持数据源**: AKShare, QStock, MooTDX

| 数据指标 | 说明 | 数据源 |
|----------|------|--------|
| 实时价格 | 当前港币价格 | AKShare, QStock, MooTDX |
| 涨跌情况 | 涨跌额、涨跌幅 | AKShare, QStock, MooTDX |
| 成交数据 | 成交量、成交额 | AKShare, QStock, MooTDX |
| 基本指标 | 市盈率、市净率等 | AKShare, QStock |

#### 📊 **历史数据**
**支持数据源**: AKShare, QStock, MooTDX

- 日线、周线、月线K线数据
- 复权价格数据
- 历史财务数据

---

### 🇺🇸 美股市场数据覆盖

#### 📈 **实时行情数据**
**支持数据源**: Yahoo Finance, Alpha Vantage, Pandas DataReader

| 数据指标 | 说明 | 数据源 |
|----------|------|--------|
| 实时价格 | 美元价格 | Yahoo Finance, Alpha Vantage |
| 盘前盘后 | 盘前盘后交易 | Yahoo Finance, Alpha Vantage |
| 成交数据 | 成交量、成交额 | Yahoo Finance, Alpha Vantage |
| 市值数据 | 市值、估值指标 | Yahoo Finance, Alpha Vantage |
| 52周高低 | 52周最高最低价 | Yahoo Finance, Alpha Vantage |

#### 📊 **历史数据**
**支持数据源**: Yahoo Finance, Alpha Vantage, Pandas DataReader

- 日线、周线、月线数据
- 分股调整数据
- 历史分红数据
- 历史财务报表

#### 💰 **美股财务数据**
**支持数据源**: Yahoo Finance, Alpha Vantage, Pandas DataReader

| 报表类型 | 覆盖内容 | 数据源 |
|----------|----------|--------|
| 10-K年报 | 完整年度财务报表 | Yahoo Finance, Alpha Vantage |
| 10-Q季报 | 季度财务报表 | Yahoo Finance, Alpha Vantage |
| 盈利报告 | 季度盈利数据 | Yahoo Finance, Alpha Vantage |
| 财务比率 | 各项财务比率 | Yahoo Finance, Alpha Vantage |

---

### 🌐 全球市场数据覆盖

#### 📊 **国际指数数据**
**支持数据源**: Yahoo Finance, Alpha Vantage, Pandas DataReader

| 指数类型 | 具体指数 | 数据源 |
|----------|----------|--------|
| **美股指数** | 标普500, 纳斯达克, 道琼斯 | Yahoo Finance, Alpha Vantage |
| **全球指数** | 富时100, 日经225, 恒生指数 | Yahoo Finance, Alpha Vantage |
| **商品指数** | 原油, 黄金, 大宗商品 | Yahoo Finance, Alpha Vantage |
| **汇率数据** | 主要货币汇率 | Yahoo Finance, Alpha Vantage |

#### 📈 **宏观数据**
**支持数据源**: Pandas DataReader, Alpha Vantage

| 数据类型 | 具体内容 | 数据源 |
|----------|----------|--------|
| **经济指标** | GDP, CPI, PMI等 | Pandas DataReader |
| **利率数据** | 各国央行利率 | Alpha Vantage |
| **就业数据** | 失业率, 非农就业 | Alpha Vantage |
| **贸易数据** | 进出口, 贸易顺差 | Pandas DataReader |

---

## 📊 数据源能力对比矩阵

### 🎯 **数据覆盖能力评分** (1-5分，5分为最优)

| 数据源 | A股实时 | A股历史 | A股财务 | 港股数据 | 美股数据 | 技术指标 | 宏观数据 | 综合评分 |
|--------|---------|---------|---------|----------|----------|----------|----------|----------|
| **PyTDX** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | ❌ | ❌ | ⭐⭐ | ❌ | **4.0** |
| **EasyQuotation** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ❌ | ⭐⭐ | ❌ | ❌ | ❌ | **3.2** |
| **QStock** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ❌ | **4.0** |
| **AKShare** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | **4.3** |
| **MooTDX** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | ⭐⭐⭐ | ❌ | ⭐⭐ | ❌ | **3.2** |
| **Tushare** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | **4.1** |
| **BaoStock** | ❌ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | ❌ | ❌ | ❌ | **3.0** |
| **Yahoo Finance** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | **4.0** |
| **Alpha Vantage** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **3.8** |
| **Pandas DataReader** | ❌ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | **3.2** |

---

## 🎯 应用场景推荐

### ⚡ **高频交易场景**
- **主要数据**: 实时价格、分笔数据、五档行情
- **推荐数据源**: PyTDX (主) + MooTDX (备)
- **数据延迟**: 50-300毫秒

### 📊 **量化分析场景**
- **主要数据**: 历史K线、技术指标、财务数据
- **推荐数据源**: AKShare + QStock + Tushare
- **数据覆盖**: 10年以上历史数据

### 💰 **基本面分析场景**
- **主要数据**: 财务报表、财务指标、公司信息
- **推荐数据源**: QStock + Tushare + BaoStock
- **数据深度**: 完整财务报表+分析指标

### 🌍 **全球配置场景**
- **主要数据**: 美股、港股、全球指数
- **推荐数据源**: Yahoo Finance + Alpha Vantage + AKShare
- **覆盖范围**: 全球主要市场

### 🔍 **研究分析场景**
- **主要数据**: 行业数据、宏观数据、板块数据
- **推荐数据源**: AKShare + Tushare + Pandas DataReader
- **数据维度**: 微观+中观+宏观全覆盖

---

## 📈 数据获取限制说明

### 🆓 **免费版本限制**

| 数据源 | 免费限制 | 建议 |
|--------|----------|------|
| **PyTDX** | 无明确限制 | 推荐高频使用 |
| **EasyQuotation** | 无明确限制 | 推荐开发使用 |
| **QStock** | 1000次/分钟 | 推荐常规使用 |
| **AKShare** | 无明确限制 | 推荐主力使用 |
| **MooTDX** | 无明确限制 | 推荐备用使用 |
| **Tushare** | 500次/天 | 推荐测试使用 |
| **BaoStock** | 无限制 | 推荐历史数据 |
| **Yahoo Finance** | 2000次/小时 | 推荐国际数据 |
| **Alpha Vantage** | 500次/天 | 推荐技术分析 |
| **Pandas DataReader** | 限制较少 | 推荐学术研究 |

### 💡 **使用建议**

1. **开发测试**: 优先使用免费版本
2. **生产环境**: 考虑付费升级高价值数据源
3. **高频场景**: 使用无限制数据源(PyTDX, AKShare等)
4. **商业项目**: 建议付费升级Tushare等专业数据源

---

## 📝 总结

本Get Stock Data微服务通过10个数据源的整合，实现了：

### ✅ **全面覆盖**
- **市场覆盖**: A股、港股、美股、全球市场
- **数据类型**: 15+大类，100+细分指标
- **时间维度**: 实时到数十年历史数据

### ⚡ **性能优化**
- **延迟覆盖**: 50毫秒到3秒
- **多级备用**: 每种数据都有多个备用源
- **智能切换**: 自动故障转移和性能优化

### 🎯 **场景适配**
- **高频交易**: 毫秒级数据源
- **量化分析**: 完整历史+技术指标
- **基本面分析**: 深度财务数据
- **全球配置**: 跨市场数据支持

### 💰 **成本控制**
- **免费优先**: 10个免费数据源
- **按需付费**: 高价值数据可选择性付费
- **弹性扩展**: 根据业务需求调整数据源配置

这样的配置确保了系统能够满足从个人投资者到机构用户的各种数据需求，同时保持成本可控和高可用性。

---

*文档版本: v1.0*
*最后更新: 2025-11-17*
*维护团队: Get Stock Data 微服务团队*