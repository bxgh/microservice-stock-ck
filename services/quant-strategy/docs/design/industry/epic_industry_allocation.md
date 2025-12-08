# EPIC-001: 行业配置建议系统

**版本**: v0.1 (草案)  
**创建日期**: 2025-12-08  
**状态**: 📝 设计中  
**优先级**: P1  
**预估工期**: 2-3 周

---

## 📋 Epic 概述

构建智能行业配置建议系统，基于多维度量化指标自动评估各行业投资价值，为长线核心仓位（70%）提供科学的行业配置建议。

### 业务目标

根据用户需求文档：
- **长线核心仓**: 配置高确定性、低估值成长股及高分红红利资产
- **目标收益**: 年化 15-25%，稳定复利
- **配置原则**: 每个行业配置 2-3 只龙头标的，构建 8-10 只股票的中线组合

### 设计理念

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        行业配置建议系统架构                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────┐      │
│   │               IndustryAllocationEngine (核心引擎)            │      │
│   └─────────────────────────────────────────────────────────────┘      │
│                              │                                          │
│        ┌─────────────────────┼─────────────────────┐                   │
│        ▼                     ▼                     ▼                   │
│   ┌─────────┐         ┌─────────────┐       ┌─────────────┐           │
│   │ 估值评分 │         │  资金评分   │       │  动量评分   │           │
│   │ Module  │         │   Module    │       │   Module    │           │
│   └─────────┘         └─────────────┘       └─────────────┘           │
│        │                     │                     │                   │
│        └─────────────────────┼─────────────────────┘                   │
│                              ▼                                          │
│                    ┌─────────────────┐                                 │
│                    │  综合评分计算   │                                 │
│                    │ Weighted Score  │                                 │
│                    └────────┬────────┘                                 │
│                             │                                          │
│                             ▼                                          │
│                    ┌─────────────────┐                                 │
│                    │  配置建议生成   │                                 │
│                    └─────────────────┘                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 待决策事项

> [!IMPORTANT]
> 以下关键设计需要您确认后再进入开发阶段

### 1. 行业分类标准

| 选项 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **A. 申万一级行业** | 31 个行业，标准化程度高 | 覆盖全面，数据源多 | 粒度较粗 |
| **B. 申万二级行业** | 134 个子行业 | 更精细 | 数据获取复杂 |
| **C. 同花顺概念板块** | 动态概念，如"AI算力" | 贴近市场热点 | 变化频繁，不稳定 |
| **D. 混合模式** | 行业 + 热点概念 | 兼顾稳定与热度 | 实现复杂度高 |

**建议**: 先实现 **A (申万一级行业)**，后续扩展概念板块

---

### 2. 评分维度与权重

| 维度 | 建议权重 | 数据指标 | 数据来源 |
|------|---------|----------|---------|
| **估值分位** | 30% | 行业 PE/PB 历史分位数 | akshare / pywencai |
| **资金流向** | 30% | 北向资金行业净流入 | akshare |
| **动量强度** | 20% | 行业指数 N 日涨跌幅 | 计算 |
| **情绪热度** | 20% | 涨停/跌停数量分布 | akshare |

**问题**: 这个权重分配是否符合您的投资风格？需要调整吗？

---

### 3. 更新频率

| 选项 | 描述 | 适用场景 |
|------|------|---------|
| **每日更新** | 收盘后计算当日评分 | 短期波段参考 |
| **每周更新** | 周末汇总周度数据 | 中线配置建议 |
| **每月更新** | 月末全面评估 | 长线战略配置 |

**建议**: 核心评分 **每周更新**，资金/情绪指标 **每日追踪**

---

### 4. 行业配置上限

| 参数 | 建议值 | 说明 |
|------|-------|------|
| 最多配置行业数 | 4-5 个 | 避免过度分散 |
| 单行业最大权重 | 25% | 风控上限 |
| 单行业标的数 | 2-3 只 | 龙头集中 |
| 最小配置权重 | 10% | 进入门槛 |

---

## 📚 User Stories 列表

### Story 001.01: 行业数据采集服务 (IndustryDataCollector)
**工期**: 3 天  
**优先级**: P0  
**依赖**: `get-stockdata` 服务

#### 目标
构建行业基础数据采集能力，从多数据源获取行业分类、成分股、行业指数等信息。

#### 数据需求

| 数据类型 | 数据源 | API | 更新频率 |
|---------|-------|-----|---------|
| 申万行业分类 | akshare | `sw_index_first_info` | 每月 |
| 行业成分股 | akshare | `index_stock_cons` | 每周 |
| 行业 PE/PB | pywencai | NL 查询 | 每日 |
| 行业涨跌幅 | pywencai | NL 查询 | 每日 |
| 北向资金行业分布 | akshare | `stock_hsgt_*` | 每日 |

#### 接口设计

```python
class IndustryDataCollector:
    """行业数据采集服务"""
    
    async def get_industry_list(self) -> pd.DataFrame:
        """
        获取行业分类列表
        
        返回:
        - industry_code: 行业代码
        - industry_name: 行业名称
        - stock_count: 成分股数量
        """
    
    async def get_industry_stocks(self, industry_code: str) -> pd.DataFrame:
        """
        获取行业成分股列表
        
        返回:
        - stock_code: 股票代码
        - stock_name: 股票名称
        - weight: 权重 (if available)
        """
    
    async def get_industry_valuation(self, industry_code: str) -> Dict:
        """
        获取行业估值数据
        
        返回:
        - pe_ttm: 滚动市盈率
        - pb: 市净率
        - pe_percentile: PE历史分位数 (近5年)
        - pb_percentile: PB历史分位数 (近5年)
        """
    
    async def get_northbound_industry_flow(self, date: str = None) -> pd.DataFrame:
        """
        获取北向资金行业流向
        
        返回:
        - industry_name: 行业名称
        - net_buy: 净买入额 (亿元)
        - net_buy_5d: 5日累计净买入
        - net_buy_20d: 20日累计净买入
        """
```

#### 验收标准

- [ ] 成功获取全部 31 个申万一级行业
- [ ] 行业成分股数据完整 (覆盖 A 股 5000+ 只)
- [ ] 估值分位数计算正确 (与同花顺数据对比验证)
- [ ] 北向资金数据延迟 < 1 天
- [ ] 单元测试覆盖率 > 80%

---

### Story 001.02: 行业估值评分模块 (ValuationScorer)
**工期**: 2 天  
**优先级**: P0

#### 目标
基于 PE/PB 历史分位数计算行业估值得分，识别低估行业。

#### 评分逻辑

```python
def calculate_valuation_score(pe_percentile: float, pb_percentile: float) -> float:
    """
    估值评分计算
    
    规则:
    - 分位数 < 20%: 极度低估, 得分 100
    - 分位数 20-40%: 低估, 得分 80
    - 分位数 40-60%: 合理, 得分 60
    - 分位数 60-80%: 偏高, 得分 40
    - 分位数 > 80%: 高估, 得分 20
    
    综合分 = PE得分 * 0.6 + PB得分 * 0.4
    """
```

#### 接口设计

```python
class ValuationScorer:
    """行业估值评分模块"""
    
    async def score_industry(self, industry_code: str) -> ValuationScore:
        """
        计算单个行业估值得分
        
        返回:
        - industry_code: 行业代码
        - pe_score: PE 得分 (0-100)
        - pb_score: PB 得分 (0-100)
        - combined_score: 综合估值得分
        - percentile_level: 估值水平 (极度低估/低估/合理/偏高/高估)
        """
    
    async def score_all_industries(self) -> pd.DataFrame:
        """批量计算所有行业估值得分"""
```

#### 验收标准

- [ ] 正确计算 PE/PB 历史分位数 (5 年窗口)
- [ ] 评分结果与人工判断一致性 > 90%
- [ ] 处理缺失数据 (新上市行业无 5 年数据)
- [ ] 性能: 全行业评分 < 10 秒

---

### Story 001.03: 资金流向评分模块 (CapitalFlowScorer)
**工期**: 2 天  
**优先级**: P0

#### 目标
基于北向资金流向计算行业资金面得分，捕捉外资配置方向。

#### 评分逻辑

```python
def calculate_capital_score(
    net_buy_today: float,
    net_buy_5d: float, 
    net_buy_20d: float
) -> float:
    """
    资金流向评分
    
    规则:
    - 短期 (当日): 权重 20%
    - 中期 (5日): 权重 40%  
    - 长期 (20日): 权重 40%
    
    每个维度按排名分档:
    - Top 10%: 100分
    - Top 30%: 80分
    - Top 50%: 60分
    - 其他: 40分
    - 净流出: 20分
    """
```

#### 验收标准

- [ ] 正确获取北向资金行业分布
- [ ] 支持多时间窗口 (1/5/10/20 日)
- [ ] 处理节假日数据缺失
- [ ] 评分合理性验证

---

### Story 001.04: 动量评分模块 (MomentumScorer)
**工期**: 1.5 天  
**优先级**: P1

#### 目标
基于行业指数相对强度计算动量得分。

#### 评分逻辑

```python
def calculate_momentum_score(
    industry_return_5d: float,
    industry_return_20d: float,
    benchmark_return: float  # 沪深300
) -> float:
    """
    动量评分
    
    规则:
    - 超额收益 = 行业涨幅 - 基准涨幅
    - 超额 > 5%: 100分
    - 超额 3-5%: 80分
    - 超额 0-3%: 60分
    - 超额 -3~0%: 40分
    - 超额 < -3%: 20分
    """
```

---

### Story 001.05: 情绪热度评分模块 (SentimentScorer)
**工期**: 1.5 天  
**优先级**: P1

#### 目标
基于涨停/跌停分布评估行业情绪热度。

#### 评分逻辑

```python
def calculate_sentiment_score(
    limit_up_count: int,    # 行业内涨停数
    limit_down_count: int,  # 行业内跌停数
    total_stocks: int       # 行业成分股总数
) -> float:
    """
    情绪热度评分
    
    规则:
    - 涨停率 = 涨停数 / 总数
    - 跌停率 = 跌停数 / 总数
    - 情绪分 = 涨停率得分 - 跌停率惩罚
    """
```

---

### Story 001.06: 综合评分引擎 (IndustryAllocationEngine)
**工期**: 2 天  
**优先级**: P0

#### 目标
整合各评分模块，生成最终行业配置建议。

#### 接口设计

```python
class IndustryAllocationEngine:
    """行业配置建议引擎"""
    
    def __init__(self, config: AllocationConfig):
        """
        初始化配置
        
        config:
        - valuation_weight: 估值权重 (default 0.3)
        - capital_weight: 资金权重 (default 0.3)
        - momentum_weight: 动量权重 (default 0.2)
        - sentiment_weight: 情绪权重 (default 0.2)
        - max_industries: 最大推荐行业数 (default 5)
        """
    
    async def calculate_scores(self) -> pd.DataFrame:
        """
        计算全行业综合评分
        
        返回:
        - industry_code
        - industry_name
        - valuation_score
        - capital_score
        - momentum_score
        - sentiment_score
        - total_score
        - rank
        """
    
    async def generate_allocation(self) -> IndustryAllocation:
        """
        生成配置建议
        
        返回:
        - recommended_industries: List[IndustryRecommendation]
        - allocation_weights: Dict[str, float]
        - generation_time: datetime
        - valid_until: datetime
        """
    
    async def get_industry_stocks_recommendation(
        self, 
        industry_code: str,
        top_n: int = 3
    ) -> List[StockRecommendation]:
        """
        获取行业内推荐标的
        
        选股条件:
        - 市值排名前 30% (龙头)
        - ROE > 10% (盈利能力)
        - 负债率 < 70% (财务稳健)
        """
```

#### 输出示例

```json
{
  "generation_time": "2025-12-08T15:30:00+08:00",
  "valid_until": "2025-12-15T15:30:00+08:00",
  "recommended_industries": [
    {
      "rank": 1,
      "industry_code": "801080",
      "industry_name": "电子",
      "total_score": 82.5,
      "scores": {
        "valuation": 75,
        "capital": 90,
        "momentum": 85,
        "sentiment": 78
      },
      "allocation_weight": 0.25,
      "recommended_stocks": ["002475.SZ", "603986.SH", "300661.SZ"],
      "reason": "估值处于近5年30%分位，北向资金连续10日净流入"
    }
  ]
}
```

---

### Story 001.07: 配置建议 API 接口
**工期**: 1 天  
**优先级**: P1

#### 目标
提供 RESTful API 供前端或其他服务调用。

#### API 设计

```yaml
# 获取行业评分列表
GET /api/v1/industry/scores
Response:
  - industry_code
  - industry_name
  - total_score
  - rank

# 获取配置建议
GET /api/v1/industry/allocation
Query:
  - max_industries: int (default 5)
  - style: str (aggressive/balanced/conservative)
Response:
  - recommended_industries
  - allocation_weights

# 获取行业详情
GET /api/v1/industry/{industry_code}
Response:
  - scores_breakdown
  - historical_scores (30d)
  - recommended_stocks

# 手动触发评分更新
POST /api/v1/industry/recalculate
```

---

## 📊 数据流图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           数据采集层                                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   akshare                  pywencai                  get-stockdata       │
│  ┌─────────┐              ┌─────────┐              ┌─────────┐          │
│  │行业分类  │              │行业PE/PB│              │行情数据  │          │
│  │北向资金  │              │涨停统计  │              │成分股   │          │
│  └────┬────┘              └────┬────┘              └────┬────┘          │
│       │                        │                        │                │
└───────┼────────────────────────┼────────────────────────┼────────────────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       IndustryDataCollector                               │
│                        (数据聚合 + 标准化)                                 │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│ValuationScorer│          │CapitalScorer │          │MomentumScorer│
│   估值评分    │          │  资金评分     │          │   动量评分   │
└───────┬──────┘          └───────┬──────┘          └───────┬──────┘
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  ▼
                    ┌────────────────────────┐
                    │ IndustryAllocationEngine│
                    │     综合评分 + 配置建议  │
                    └────────────┬───────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │      REST API          │
                    │   /api/v1/industry/*   │
                    └────────────────────────┘
```

---

## ✅ 验收标准总览

| Story | 核心验收点 | 优先级 |
|-------|-----------|--------|
| 001.01 | 31 个行业数据完整，成分股覆盖 5000+ | P0 |
| 001.02 | 估值评分与同花顺一致性 > 90% | P0 |
| 001.03 | 北向资金多时间窗口正确 | P0 |
| 001.04 | 动量超额收益计算正确 | P1 |
| 001.05 | 情绪指标与实际涨停数匹配 | P1 |
| 001.06 | 综合评分逻辑正确，配置建议合理 | P0 |
| 001.07 | API 可用，响应 < 1s | P1 |

---

## 🔗 依赖关系

```
get-stockdata 服务 (EPIC-007)
        │
        │  提供: 行情数据, 榜单数据, 指数成分
        ▼
EPIC-001: 行业配置建议系统 (本 EPIC)
        │
        │  输出: 行业评分, 配置建议
        ▼
后续 EPIC: 波段交易信号生成器
```

---

## 📝 备注

1. **数据源验证**: 在 Story 001.01 开始前，需要先验证 `akshare` 和 `pywencai` 的行业数据接口可用性
2. **性能要求**: 全行业评分计算应 < 30 秒，支持缓存
3. **回测支持**: 后续可扩展历史评分回测功能
