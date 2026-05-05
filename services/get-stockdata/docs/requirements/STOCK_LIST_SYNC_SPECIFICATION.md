# Story 2.4 数据需求

**需求方**: quant-strategy (EPIC-002 Story 2.4)  
**提供方**: get-stockdata  
**优先级**: P0  
**日期**: 2025-12-15

---

## 需求概述

Story 2.4 需要实现**核心股票池管理**，从全市场筛选出高质量股票。需要一个包含全市场股票的基础列表作为筛选起点。

---

## 数据需求

### 接口: `GET /api/v1/stocks/list`

**当前问题**: 返回空列表 (`data: []`, `total: 0`)

**期望**: 返回A股全市场股票列表 (~5000只)

**必需字段**:
```json
{
  "code": "600519",        // 股票代码
  "name": "贵州茅台",      // 股票名称  
  "exchange": "SH",        // 交易所 (SH/SZ/BJ)
  "industry": "酿酒行业"   // 行业分类 (用于分组排序)
}
```

**可选字段** (如果容易提供):
```json
{
  "sector": "食品饮料",     // 板块
  "list_date": "2001-08-27", // 上市日期
  "is_active": true          // 是否活跃交易
}
```

---

## 使用场景

Story 2.4 的筛选流程:
```
全市场股票列表 (5000只)
  ↓ 第一轮: 风险过滤 (剔除ST/停牌等)
剩余 ~4000只
  ↓ 第二轮: 基本面评分 (ROE/Growth/Quality)
  ↓ 第三轮: 估值评分 (PE/PB Band)
  ↓ 第四轮: 按行业分组, 取Top N
核心股票池 (~100-200只)
```

**关键点**: 
- 需要 `industry` 字段进行**行业分组**
- 需要完整的市场覆盖，否则会遗漏优质股票

---

## 验证标准

### Test 1: 数量验证
```bash
curl http://127.0.0.1:8083/api/v1/stocks/list?limit=10
# 期望: data 数组包含 10 只股票, total >= 4000
```

### Test 2: 字段验证
```bash
curl http://127.0.0.1:8083/api/v1/stocks/list?limit=1
# 期望: 返回的股票对象包含 code, name, exchange, industry
```

### Test 3: 行业覆盖验证
```bash
curl http://127.0.0.1:8083/api/v1/stocks/list?limit=100
# 期望: industry 字段有值且多样化 (至少覆盖10+个行业)
```

---

## 补充说明

- **数据源**: 不限 (AkShare/Baostock/Tushare 均可)
- **更新频率**: 每天更新一次即可 (股票列表变化不频繁)
- **缓存策略**: 由 get-stockdata 自行决定

---

**需求确认后即可开始 Story 2.4 开发。**
