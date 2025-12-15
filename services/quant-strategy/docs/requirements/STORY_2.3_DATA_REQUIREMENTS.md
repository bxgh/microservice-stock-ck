# Story 2.3 数据需求文档

**需求方**: quant-strategy (EPIC-002 Story 2.3)  
**提供方**: get-stockdata  
**优先级**: P0 (阻塞 Story 2.3 实施)  
**日期**: 2025-12-15

---

## 一、需求概述

Story 2.3 需要实现 **估值分析器 (Valuation Analyzer)**,采用 **PE/PB Band 估值法** 计算股票估值评分 (0-100分)。

### 核心方法
- 获取股票 3-5 年历史 PE/PB 数据
- 计算当前 PE/PB 在历史分布中的百分位
- 低百分位 (< P25) = 低估 → 高评分
- 高百分位 (> P75) = 高估 → 低评分

### 数据依赖
需要 `get-stockdata` 服务提供完整的估值数据接口。

---

## 二、API 现状检查

### API 1: 当前估值数据
**Endpoint**: `GET /api/v1/market/valuation/{stock_code}`  
**状态**: ⚠️ **500 Internal Server Error**

**测试结果**:
```bash
$ curl http://127.0.0.1:8083/api/v1/market/valuation/600519
# 长时间无响应后返回 500 错误
```

**路由状态**: ✅ 已定义 (`valuation_routes.py`)  
**服务状态**: ❌ `ValuationService.get_current_valuation()` 实现缺失或有bug

---

### API 2: 历史估值数据
**Endpoint**: `GET /api/v1/market/valuation/{stock_code}/history`  
**状态**: ⚠️ **500 Internal Server Error** (18秒超时)

**测试结果**:
```bash
$ curl http://127.0.0.1:8083/api/v1/market/valuation/600519/history
# HTTP/1.1 500 Internal Server Error (18秒后)
```

**路由状态**: ✅ 已定义 (`valuation_routes.py`)  
**服务状态**: ❌ `ValuationService.get_valuation_history()` 实现缺失或有bug

---

## 三、所需数据字段

### 3.1 当前估值数据 (`GET /valuation/{code}`)

**必需字段** (P0):
```json
{
  "stock_code": "600519",
  "report_date": "2025-12-15",
  "total_market_cap": 2500.0,          // 总市值 (亿元)
  "circulating_market_cap": 2500.0,    // 流通市值 (亿元)
  "pe_ttm": 35.5,                      // 滚动市盈率 (TTM)
  "pb_ratio": 12.3                     // 市净率
}
```

**可选字段** (P1):
```json
{
  "pe_static": 33.2,                   // 静态市盈率
  "ps_ratio": 8.5,                     // 市销率
  "pcf_ratio": 25.0,                   // 市现率
  "dividend_yield_ttm": 1.2            // 股息率 (TTM)
}
```

---

### 3.2 历史估值数据 (`GET /valuation/{code}/history`)

**请求参数**:
- `years`: int (默认5, 范围1-10) - 历史年数
- `frequency`: str (D/W/M) - 频率 (日/周/月)

**响应结构**:
```json
{
  "stock_code": "600519",
  "years": 5,
  "frequency": "D",
  
  "stats": {
    "pe_ttm": {
      "mean": 32.5,
      "median": 30.2,
      "p25": 25.0,      // 25th Percentile
      "p50": 30.2,      // 50th Percentile
      "p75": 38.0,      // 75th Percentile
      "p90": 45.0,
      "min": 18.0,
      "max": 60.0,
      "current": 35.5,
      "percentile": 62.5  // 当前值的百分位 (0-100)
    },
    "pb_ratio": {
      "mean": 10.8,
      "median": 10.5,
      "p25": 8.2,
      "p50": 10.5,
      "p75": 13.0,
      "p90": 15.5,
      "min": 5.0,
      "max": 18.0,
      "current": 12.3,
      "percentile": 68.3
    }
  },
  
  "dates": ["2020-12-15", "2020-12-16", ...],
  "pe_ttm_list": [28.5, 29.1, ...],
  "pb_ratio_list": [9.8, 10.1, ...]
}
```

**关键说明**:
1. `stats` 是 **必需字段** (P0) - 用于计算Band评分
2. `dates` 和时间序列列表是 **可选字段** (P2) - 仅用于可视化

---

## 四、数据源建议

### 推荐方案 1: Tushare Pro (推荐)
```python
import tushare as ts

# 当前估值
df = ts.pro_bar(ts_code='600519.SH', adj='qfq', asset='E')
# 包含字段: pe_ttm, pb, ps_ttm, total_mv, circ_mv

# 历史估值
df_history = ts.pro_bar(
    ts_code='600519.SH',
    start_date='20200101',
    end_date='20251215',
    fields='trade_date,pe_ttm,pb'
)
```

### 推荐方案 2: AkShare (免费备选)
```python
import akshare as ak

# 实时估值
df = ak.stock_zh_a_spot_em()  # 包含 pe_ttm, pb
# 或
df = ak.stock_individual_info_em(symbol='600519')

# 历史数据:需组合接口
# Price History + Financial History => 计算历史 PE/PB
```

---

## 五、实施优先级

### Phase 1: 修复当前估值接口 (P0 - 1周)
- ✅ 路由已存在
- ❌ 修复 `ValuationService.get_current_valuation()`
- 🎯 **阻塞**: Story 2.3 基础功能

### Phase 2: 实现历史估值接口 (P0- 1周)
- ✅ 路由已存在
- ❌ 实现 `ValuationService.get_valuation_history()`
- 🎯 **阻塞**: Story 2.3 PE/PB Band 评分

---

## 六、验证标准

### API 1 验证
```bash
curl http://127.0.0.1:8083/api/v1/market/valuation/600519
# 期望: HTTP 200, 返回包含 pe_ttm, pb_ratio 的JSON
```

### API 2 验证
```bash
curl "http://127.0.0.1:8083/api/v1/market/valuation/600519/history?years=5&frequency=D"
# 期望: HTTP 200, 返回包含 stats.pe_ttm.p25/p50/p75 的JSON
```

---

## 七、临时 Workaround (如无法及时实现)

**Option A**: quant-strategy 自行计算
- 从 `/finance/history` 获取历史财务数据
- 从 `/quotes/history` 获取历史价格
- 自行计算: `PE = Price / EPS`, `PB = Price / BVPS`
- **缺点**: 性能差, 计算复杂

**Option B**: 简化估值评分
- 跳过 Band 分析
- 使用固定阈值 (如 PE < 20 = 低估)
- **缺点**: 不考虑行业/历史差异, 准确性低

---

## 八、联系方式

**需求方**: quant-strategy 开发团队  
**数据提供方**: get-stockdata 开发团队

**问题反馈**:
1. 当前 500 错误的具体原因?
2. `ValuationService` 实现进度?
3. 数据源选择 (Tushare vs AkShare)?
4. 实施时间线 (Story 2.3 等待中)?

---

**文档版本**: 1.0  
**最后更新**: 2025-12-15  
**状态**: 待 get-stockdata 团队响应
