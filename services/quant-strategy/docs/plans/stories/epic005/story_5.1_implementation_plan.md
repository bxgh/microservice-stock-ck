# Story 5.1 Implementation Plan: Universe Pool

**Story ID**: 5.1  
**Story Name**: Universe Pool - 全市场基础池  
**开始日期**: 2025-12-13  
**预期完成**: 2025-12-13  
**优先级**: P0

---

## 📋 概述

构建全市场股票的基础筛选池，过滤掉明显不合格的标的。Universe Pool 是所有策略的输入源，不涉及任何策略逻辑。

### 验收标准
- [ ] 能从 `get-stockdata` 获取全市场股票列表
- [ ] 自动剔除 ST/*ST 股票
- [ ] **筛选条件可动态配置（通过数据库/API）**
- [ ] **数据持久化到腾讯云 MySQL**
- [ ] **由 task-scheduler 服务触发定时刷新**
- [ ] Universe Pool 数量稳定在 2800-3500 只

---

## 🔗 依赖分析

### 上游依赖
| 依赖项 | 状态 | 说明 |
|--------|------|------|
| EPIC-001 基础设施 | ✅ 已完成 | Database, StockDataProvider |
| `get-stockdata` `/api/v1/stocks/list` | ✅ 可用 | 股票列表接口 |
| `task-scheduler` 微服务 | ✅ 可用 | 外部任务调度 |
| 腾讯云 MySQL | ✅ 已配置 | `sh-cdb-h7flpxu4.sql.tencentcdb.com:26300` |

---

## 📦 Proposed Changes

### 1. 动态筛选配置

#### [NEW] filter_config_models.py
`src/database/filter_config_models.py`

```python
class UniverseFilterConfig(Base):
    """Universe Pool 筛选配置 (动态可调)"""
    __tablename__ = 'universe_filter_configs'
    
    id: int (PK)
    config_name: str (配置名称, default='default')
    
    # 筛选参数 (可动态调整)
    min_list_months: int = 12         # 上市最少月份
    min_avg_turnover: float = 3000    # 日均成交额 (万元)
    min_market_cap: float = 30        # 最小市值 (亿元)
    min_turnover_ratio: float = 0.3   # 最低换手率 (%)
    
    # 配置状态
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
```

**API 端点**:
```http
GET  /api/v1/pools/universe/config     # 获取当前配置
PUT  /api/v1/pools/universe/config     # 更新配置
POST /api/v1/pools/universe/config/reset  # 重置为默认
```

---

### 2. 股票池数据模型

#### [NEW] stock_pool_models.py
`src/database/stock_pool_models.py`

```python
class UniverseStock(Base):
    """全市场基础池 - 存储到腾讯云 MySQL"""
    __tablename__ = 'universe_stocks'
    
    id: int (PK)
    code: str (股票代码, unique, indexed)
    name: str (股票名称)
    list_date: date (上市日期)
    exchange: str (交易所: SH/SZ/BJ)
    
    # 流动性指标
    avg_turnover_20d: float (日均成交额, 万元)
    market_cap: float (总市值, 亿元)
    turnover_ratio_20d: float (20日换手率, %)
    
    # 筛选结果
    is_qualified: bool (是否合格)
    disqualify_reason: str (不合格原因)
    
    updated_at: datetime
    created_at: datetime

class PoolTransition(Base):
    """池流转历史"""
    __tablename__ = 'pool_transitions'
    
    id: int (PK)
    code: str (indexed)
    from_pool: str
    to_pool: str
    transition_date: datetime
    reason: str
```

---

### 3. 外部调度器集成

> [!IMPORTANT]
> **不使用内部 BackgroundTaskManager**，改为由 `task-scheduler` 微服务调用 API。

#### [NEW] stock_pool_routes.py
`src/api/stock_pool_routes.py`

```python
# 供 task-scheduler 调用的触发端点
POST /api/v1/pools/universe/refresh
Request: { "triggered_by": "task-scheduler", "job_id": "xxx" }
Response: { "success": true, "stats": {...} }

# 查询接口
GET /api/v1/pools/universe         # 查询 Universe Pool
GET /api/v1/pools/universe/stats   # 池统计信息
GET /api/v1/pools/universe/config  # 获取筛选配置
PUT /api/v1/pools/universe/config  # 更新筛选配置
```

**task-scheduler 配置示例**:
```yaml
# task-scheduler 中配置
jobs:
  - name: refresh_universe_pool
    cron: "0 22 * * 0"  # 每周日 22:00
    target:
      service: quant-strategy
      endpoint: /api/v1/pools/universe/refresh
      method: POST
```

---

### 4. 核心服务

#### [NEW] universe_pool_service.py
`src/services/stock_pool/universe_pool_service.py`

```python
class UniversePoolService:
    """Universe Pool 管理服务"""
    
    async def refresh_universe_pool(
        self, 
        config: Optional[UniverseFilterConfig] = None
    ) -> RefreshResult:
        """刷新 Universe Pool (使用动态配置)"""
        # 1. 获取配置 (如未传入则读取数据库)
        config = config or await self._get_active_config()
        # 2. 从 get-stockdata 获取全市场
        # 3. 应用筛选规则
        # 4. 持久化到腾讯云 MySQL
        
    async def get_qualified_stocks() -> List[UniverseStock]
    async def get_pool_stats() -> PoolStats
    async def update_filter_config(config: dict) -> UniverseFilterConfig
```

**筛选流程**:
```
get-stockdata API → 全市场 (~5000只)
    ↓
[Filter] 非 ST/*ST
    ↓
[Filter] 上市时间 >= config.min_list_months
    ↓
[Filter] 日均成交额 >= config.min_avg_turnover
    ↓
[Filter] 市值 >= config.min_market_cap
    ↓
[Filter] 换手率 >= config.min_turnover_ratio
    ↓
Universe Pool → 腾讯云 MySQL
```

---

## 📁 新增文件清单

| 路径 | 描述 |
|------|------|
| `src/database/stock_pool_models.py` | 股票池 ORM 模型 |
| `src/database/filter_config_models.py` | 筛选配置 ORM 模型 |
| `src/services/stock_pool/__init__.py` | 服务包初始化 |
| `src/services/stock_pool/universe_pool_service.py` | 核心服务 |
| `src/api/stock_pool_routes.py` | API 路由 |
| `tests/test_universe_pool.py` | 集成测试 |

---

## 🧪 Verification Plan

### 集成测试
```bash
docker exec quant-strategy-dev pytest tests/test_universe_pool.py -v
```

**测试用例**:
1. 成功从 API 获取股票列表
2. ST 股票被正确过滤
3. **动态配置生效（修改阈值后重新筛选）**
4. **数据成功写入腾讯云 MySQL**
5. 筛选后数量在 2800-3500 范围内

---

## ⏱️ 预计工期

| 任务 | 工时 |
|------|------|
| 数据模型 + 配置模型 | 0.5h |
| UniversePoolService (含动态配置) | 1.5h |
| StockDataProvider 扩展 | 0.5h |
| API 路由 (含配置 CRUD) | 0.5h |
| 测试 | 1h |
| **合计** | **4h (0.5天)** |
