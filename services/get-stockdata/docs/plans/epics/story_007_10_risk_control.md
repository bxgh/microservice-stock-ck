# Story 007.10: 风控数据服务 (RiskControlService)

**状态**: 📝 待开发  
**优先级**: P1 (量化策略风控依赖)  
**预估工期**: 2-3 天  
**需求方**: quant-strategy 服务 (EPIC-002: 长线资产配置系统)

---

## 📋 需求背景

量化策略的"负面清单排雷系统" (Risk Veto Filter) 需要在股票评分前进行风险过滤，防止资金流入高风险标的。当前 `get-stockdata` 服务已提供基础财务数据 (PE/PB/财务摘要)，但**缺少风控决策所需的关键指标**。

### 业务价值
- **资本保护**: 避免踩雷 ST 股、高商誉暴雷股、质押爆仓股。
- **合规性**: 排除监管黑名单股票。
- **质量识别**: 区分"纸面富贵"和真实盈利能力。

---

## 🎯 需求清单

### 1. ST/退市风险标记
**字段**: `is_st`, `risk_level`  
**说明**: 标识股票是否为 ST、*ST、退市整理等高风险状态。

**数据源建议**:
- **akshare**: `stock_info_a_code_name()` - 返回所有 A 股基本信息，包含股票名称（可通过名称判断 ST）
- **pywencai**: 自然语言查询 `"ST股票"` 或 `"退市风险股票"`

**返回格式**:
```json
{
  "code": "600001",
  "name": "邯郸钢铁",
  "is_st": false,
  "is_star_st": false,
  "is_delisting": false,
  "risk_level": "normal"  // normal | st | star_st | delisting
}
```

---

### 2. 商誉风险指标
**字段**: `goodwill`, `net_assets`, `goodwill_ratio`  
**说明**: 商誉占净资产比例过高（如 >30%）是减值暴雷的重要信号。

**数据源建议**:
- **akshare**: `stock_financial_abstract_ths()` - 同花顺财务摘要
- **tushare** (如可用): `balancesheet` - 资产负债表

**计算公式**:
```python
goodwill_ratio = goodwill / net_assets
```

**返回格式**:
```json
{
  "code": "600001",
  "goodwill": 1500000000.0,        // 商誉 (元)
  "net_assets": 5000000000.0,      // 净资产 (元)
  "goodwill_ratio": 0.30,          // 商誉比例
  "report_date": "2024-09-30"      // 报告期
}
```

---

### 3. 股权质押风险
**字段**: `pledge_ratio`, `major_shareholder_pledge`  
**说明**: 大股东质押比例过高（如 >50%）存在爆仓平仓风险。

**数据源建议**:
- **akshare**: `stock_pledge_stat()` - 股权质押统计
- **pywencai**: 查询 `"大股东质押比例超过50%"`

**返回格式**:
```json
{
  "code": "600001",
  "total_pledge_ratio": 0.35,          // 总质押比例
  "major_shareholder_pledge": 0.45,    // 大股东质押比例
  "latest_date": "2024-12-01"
}
```

---

### 4. 监管违规记录
**字段**: `regulatory_events`, `violation_count`  
**说明**: 近 12 个月的立案调查、违规处罚、退市预警等。

**数据源建议**:
- **akshare**: `stock_info_sh_delist()` - 上交所退市风险
- **pywencai**: `"被证监会立案调查"`, `"收到监管函"`
- **备用**: 爬取交易所公告或证监会官网

**返回格式**:
```json
{
  "code": "600001",
  "events": [
    {
      "date": "2024-11-15",
      "type": "investigation",       // investigation | penalty | warning
      "severity": "high",             // high | medium | low
      "description": "证监会立案调查财务造假"
    }
  ],
  "violation_count_12m": 1,          // 近12个月违规次数
  "has_critical_risk": true
}
```

---

### 5. 现金流健康度
**字段**: `operating_cash_flow`, `net_profit`, `cash_flow_ratio`  
**说明**: 经营性现金流 / 净利润 < 0.5 表明利润含金量低，可能存在财务粉饰。

**数据源建议**:
- **akshare**: `stock_financial_abstract_ths()` - 财务摘要（包含现金流）
- **tushare** (如可用): `cashflow` - 现金流量表

**计算公式**:
```python
cash_flow_ratio = operating_cash_flow / net_profit
# 健康标准: > 1.0 (优秀), 0.5-1.0 (正常), < 0.5 (警惕)
```

**返回格式**:
```json
{
  "code": "600001",
  "operating_cash_flow": 800000000.0,  // 经营性现金流净额 (元)
  "net_profit": 1000000000.0,          // 净利润 (元)
  "cash_flow_ratio": 0.80,
  "health_status": "normal",           // excellent | normal | warning
  "report_date": "2024-09-30"
}
```

---

## 📡 API 设计

### Endpoint 1: 批量风控数据查询

```http
GET /api/v1/risk-control/batch
```

**Query Parameters**:
- `codes`: 股票代码列表（逗号分隔），如 `600000,000001,300001`
- `fields`: 可选，指定返回字段，如 `st,goodwill,pledge`（默认全返回）

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "code": "600001",
      "name": "邯郸钢铁",
      "risk_profile": {
        "st_status": { "is_st": false, "risk_level": "normal" },
        "goodwill": { "goodwill_ratio": 0.15, "report_date": "2024-09-30" },
        "pledge": { "major_shareholder_pledge": 0.25 },
        "regulatory": { "violation_count_12m": 0, "has_critical_risk": false },
        "cash_flow": { "cash_flow_ratio": 0.85, "health_status": "normal" }
      }
    }
  ],
  "metadata": {
    "total": 1,
    "data_source": "akshare",
    "cache_hit": false,
    "latency_ms": 245
  }
}
```

### Endpoint 2: ST 股票列表

```http
GET /api/v1/risk-control/st-list
```

**Response**:
```json
{
  "success": true,
  "data": {
    "st_stocks": ["600001", "600002"],
    "star_st_stocks": ["000003"],
    "delisting_stocks": ["300004"],
    "total_count": 197,
    "update_time": "2024-12-08T10:00:00"
  }
}
```

---

## 🧪 验收标准

### 功能测试
- [ ] 能正确识别 ST/*ST 股票（测试已知 ST 股如 *ST 海润）
- [ ] 商誉比例计算准确（对比东方财富手工数据）
- [ ] 质押数据完整性 >80%（A 股主板前 100 只）
- [ ] 现金流比例计算逻辑与会计准则一致

### 性能测试
- [ ] 批量查询 100 只股票 < 3 秒
- [ ] 缓存命中率 >70%（相同请求 1 分钟内）

### 数据质量
- [ ] ST 状态准确率 100%（零容忍，直接影响风控）
- [ ] 财务数据时效性：最新季报数据 < 7 天延迟

---

## 🔧 实现建议

### 技术方案
1. **新建服务类**: `services/data_service/risk_control_service.py`
2. **数据源优先级**:
   - ST 状态: akshare (实时) → pywencai (备用)
   - 财务数据: akshare 财务摘要 → tushare (如可用)
   - 监管事件: pywencai 自然语言查询
3. **缓存策略**:
   - ST 状态: TTL=1小时（可能日内变更）
   - 财务数据: TTL=24小时（季报发布后才更新）
   - 监管事件: TTL=6小时（新闻时效性）

### 代码示例 (伪代码)
```python
class RiskControlService(DataServiceBase):
    async def get_risk_profile(self, codes: List[str]) -> Dict:
        # 1. 检查 ST 状态 (akshare)
        st_data = await self._fetch_st_status(codes)
        
        # 2. 获取财务数据 (akshare)
        financials = await self._fetch_financials(codes)
        
        # 3. 计算风险指标
        risk_profiles = self._calculate_risk_metrics(st_data, financials)
        
        return risk_profiles
```

---

## 📦 依赖与前置条件

- ✅ EPIC-007 Story 007.01 核心框架（已完成）
- ✅ EPIC-007 Story 007.08 财务服务（已完成基础）
- ⚠️ akshare 反爬限制解决（如遇到需处理）
- ⚠️ pywencai Node.js 环境（已有）

---

## 📌 优先级说明

**为何是 P1**:
- 长线资产配置系统 (EPIC-002) 的第一步就是风控过滤，无此数据无法推进。
- 风控失误的代价远高于收益优化，是"负收益"而非"少赚"。

**建议开发顺序**:
1. **Phase 1** (1天): ST 状态 + 商誉比例（最关键）
2. **Phase 2** (1天): 质押数据 + 现金流健康度
3. **Phase 3** (0.5天): 监管事件 + 单元测试

---

## 🔗 相关文档

- [EPIC-002: 长线资产配置系统](file:///home/bxgh/microservice-stock/services/quant-strategy/docs/plans/epics/epic002_long_term_allocation.md)
- [Risk Veto Filter 实施计划](file:///home/bxgh/.gemini/antigravity/brain/c8fef047-e1eb-46bf-9b29-bb5cb7aa41aa/implementation_plan.md)
- [get-stockdata EPIC-007 数据服务](file:///home/bxgh/microservice-stock/services/get-stockdata/docs/plans/epics/epic007_data_service_stories.md)
