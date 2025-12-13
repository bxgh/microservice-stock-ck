# Story 5.1 验收演示 (Universe Pool)

**Story ID**: 5.1  
**完成日期**: 2025-12-13  
**状态**: ✅ 已完成

---

## 1. 功能演示

### 1.1 核心组件

| 组件 | 文件 | 说明 |
|------|------|------|
| **UniverseFilterConfig** | `database/stock_pool_models.py` | 动态筛选配置模型 |
| **UniverseStock** | `database/stock_pool_models.py` | 股票池存储模型 |
| **UniversePoolService** | `services/stock_pool/universe_pool_service.py` | 核心业务逻辑 |
| **Stock Pool Routes** | `api/stock_pool_routes.py` | REST API 端点 |

### 1.2 API 端点

```http
GET  /api/v1/pools/universe          # 查询 Universe Pool
GET  /api/v1/pools/universe/stats    # 池统计信息
POST /api/v1/pools/universe/refresh  # 刷新 (供 task-scheduler 调用)
GET  /api/v1/pools/universe/config   # 获取筛选配置
PUT  /api/v1/pools/universe/config   # 更新筛选配置
POST /api/v1/pools/universe/config/reset  # 重置为默认
```

### 1.3 API 测试结果

**获取筛选配置**:
```bash
$ curl http://localhost:8084/api/v1/pools/universe/config
```
```json
{
  "config_name": "default",
  "min_list_months": 12,
  "min_avg_turnover": 3000.0,
  "min_market_cap": 30.0,
  "min_turnover_ratio": 0.3,
  "is_active": true,
  "updated_at": "2025-12-13T19:00:48"
}
```

---

## 2. 设计亮点

### 2.1 动态筛选配置
筛选参数存储在数据库表 `universe_filter_configs` 中，可通过 API 动态调整，无需重新部署：

```python
# 更新筛选阈值
PUT /api/v1/pools/universe/config
{
  "min_market_cap": 50.0,  # 提高市值门槛到 50 亿
  "min_avg_turnover": 5000  # 提高成交额门槛到 5000 万
}
```

### 2.2 外部调度器集成
符合编程规范，由 `task-scheduler` 微服务调用 API 触发刷新，不使用内部定时任务：

```yaml
# task-scheduler 配置
jobs:
  - name: refresh_universe_pool
    cron: "0 22 * * 0"  # 每周日 22:00
    target:
      service: quant-strategy
      endpoint: /api/v1/pools/universe/refresh
      method: POST
```

### 2.3 腾讯云 MySQL 持久化
数据存储到腾讯云 MySQL，符合编程规范：
- Host: `sh-cdb-h7flpxu4.sql.tencentcdb.com:26300`
- Database: `alwaysup`

---

## 3. 交付文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `src/database/stock_pool_models.py` | NEW | ORM 模型 |
| `src/services/stock_pool/__init__.py` | NEW | 服务包初始化 |
| `src/services/stock_pool/universe_pool_service.py` | NEW | 核心服务 |
| `src/api/stock_pool_routes.py` | NEW | API 路由 |
| `src/adapters/stock_data_provider.py` | MODIFIED | 新增 `get_all_stocks()` |
| `src/database/__init__.py` | MODIFIED | 导出新模型 |
| `src/main.py` | MODIFIED | 注册新路由 |
| `docs/CODING_STANDARDS.md` | MODIFIED | 新增数据库/调度器规范 |

---

## 4. 后续步骤

1. **测试刷新功能**: 调用 `POST /api/v1/pools/universe/refresh` 验证全市场筛选
2. **配置 task-scheduler**: 添加周日定时刷新任务
3. **继续 Story 5.4**: 实现 Position Pool (持仓池)
