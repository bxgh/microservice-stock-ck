# API 接口路由层 (API Route Layer)

**实现路径**: `src/api/` (被动响应模式)

## 1. 运行模式：被动响应 (Passive Mode)

本层是 `get-stockdata` 作为数据接口服务的体现。它处于“待命”状态，仅在接收到量化策略引擎或其他外部服务请求时才执行。

### 核心技术栈: FastAPI
- **异步处理**: 全部 Router 方法使用 `async def` 以支持高性能 IO。
- **参数验证**: 使用 `Pydantic` 模型进行严格的参数验证（如代码格式、日期范围）。

---

## 2. 路由模块划分

| 模块 | 路由前缀 | 关联 Service | 描述 |
| :--- | :--- | :--- | :--- |
| **Quotes** | `/api/v1/quotes` | `QuotesService` | 提供实时快照、分笔查询。 |
| **Finance** | `/api/v1/finance` | `FinancialService` | 获取财务报表、核心指标。 |
| **Market** | `/api/v1/market` | `IndustryService` | 板块排名、行业成分。 |
| **History** | `/api/v1/quotes/history` | `HistoryService` | 历史 K 线、数据导出。 |

---

## 3. 请求响应标准 (Standardization)

为了确保下游（如 `quant-strategy`）的处理一致性，路由层强制执行以下标准：

1.  **代码标准化**: 内部调用 `clean_stock_code` 确保不带 prefix。但在 API 返回时，根据接口定义决定是否保留装饰符号。
2.  **错误处理**: 使用自定义 `HTTPException` 处理数据源缺失、参数非法等情况，返回统一的 JSON 错误体。
3.  **结果转换**: 自动处理 NumPy/Pandas 对象在序列化时的类型转换（如 `NaN` 转 `null`）。

---

## 4. 后台同步控制接口

API 层不仅用于数据查询，还暴露了手动触发后台任务的端点：
- `POST /api/v1/sync/kline`: 触发 `gsd-worker` 执行 K 线同步。
- `GET /api/v1/sync/status`: 查询当前同步任务进度。
