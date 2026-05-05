# Story 007.10 风控数据服务 - 开发交接说明

## 📋 快速上手

**目标**: 为 `quant-strategy` 服务的风控过滤系统提供必需的财务风险数据。

**核心文档**: [story_007_10_risk_control.md](./story_007_10_risk_control.md)

---

## 🎯 开发优先级

### Phase 1: 最小可用版本 (MVP - 1天)
**目标**: 让 quant-strategy 能完成基本风控过滤

必须实现:
- ✅ **ST 状态检测**: `GET /api/v1/risk-control/st-list`
- ✅ **商誉比例**: 从财务摘要提取 `goodwill` 和 `net_assets`

**验收**: 能识别 100 只测试股票中的 ST 股，商誉比例计算准确率 >95%

---

### Phase 2: 完整功能 (1-1.5天)
新增:
- ✅ 质押数据
- ✅ 现金流健康度
- ✅ 批量查询接口: `GET /api/v1/risk-control/batch`

---

### Phase 3: 增强版 (可选 - 0.5天)
- ✅ 监管违规记录
- ✅ 性能优化（Redis 缓存）

---

## 🔧 技术实现要点

### 1. 数据源选择矩阵

| 指标 | 首选数据源 | 备用方案 | 更新频率 |
|-----|----------|---------|---------|
| ST状态 | akshare `stock_info_a_code_name()` | pywencai "ST股票" | 1小时 |
| 商誉 | akshare `stock_financial_abstract_ths()` | tushare `balancesheet` | 24小时 |
| 质押 | akshare `stock_pledge_stat()` | - | 24小时 |
| 现金流 | akshare `stock_financial_abstract_ths()` | - | 24小时 |
| 监管 | pywencai (自然语言) | 手工维护黑名单 | 6小时 |

### 2. 代码位置

**新建文件**:
```
services/get-stockdata/src/
├── services/
│   └── data_service/
│       └── risk_control_service.py    # 核心服务类
├── api/
│   └── routers/
│       └── risk_control_routes.py     # API 路由
└── tests/
    └── test_risk_control_service.py   # 单元测试
```

**修改文件**:
- `services/data_service/manager.py`: 注册 RiskControlService
- `main.py`: 引入 risk_control_routes

---

## 🧪 测试建议

### 单元测试用例
```python
# test_risk_control_service.py

async def test_st_status_detection():
    """测试 ST 状态识别"""
    service = RiskControlService()
    result = await service.get_st_status(["600001", "ST600002"])
    
    assert result["600001"]["is_st"] == False
    assert result["ST600002"]["is_st"] == True

async def test_goodwill_ratio_calculation():
    """测试商誉比例计算"""
    # Mock 数据: 商誉=300亿，净资产=1000亿
    result = service._calculate_goodwill_ratio(
        goodwill=30000000000,
        net_assets=100000000000
    )
    assert result == 0.30
```

### 手工验证
1. 访问 `http://localhost:8080/api/v1/risk-control/st-list`
2. 确认返回包含已知 ST 股（如 *ST海润）
3. 批量查询接口测试 100 只股票 < 3秒

---

## ⚠️ 已知风险点

1. **akshare 反爬**: 如遇到限流，切换到 pywencai 或加延迟
2. **财务数据延迟**: 季报发布后可能 3-7 天才能拿到数据
3. **监管事件**: 没有标准 API，需要自然语言查询或爬虫

---

## 📞 联系方式

**需求方**: quant-strategy 开发团队  
**阻塞影响**: EPIC-002 Story 2.1 无法开发  
**紧急程度**: P1（建议 2 天内完成 MVP）

如有技术疑问，请查阅:
- [完整需求文档](./story_007_10_risk_control.md)
- [EPIC-002 风控设计](file:///home/bxgh/microservice-stock/services/quant-strategy/docs/plans/epics/epic002_long_term_allocation.md)
