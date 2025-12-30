# 质控报告 (Quality Control Report) - Story 10.2 & Scanner Engine

**执行日期**: 2025-12-30  
**审查范围**: `feature/quant-strategy` (f86b7c9..6ffe9d2)  
**重点领域**: 量化策略引擎、数据采集微服务、gRPC 架构、代码标准合规性

---

## 🟢 核心优势 (Strong Points)

1.  **架构解耦 (Decoupling)**: 
    - `get-stockdata` 已成功重构为纯 API 层，通过 gRPC 与 `mootdx-source` 通信，极大地简化了 API 层的逻辑。
    - `data-collector` 的引入实现了采集与应用的分离，符合微服务架构原则。
2.  **并发性与健壮性 (Concurrency & Resilience)**:
    - `StrategyRegistry` 使用了单例模式和 `asyncio.Lock` 保护，其 `_ensure_lock` 机制优雅地解决了多事件循环环境下的 Lock 绑定问题。
    - `DataSourceCollector` 使用 `asyncio.Semaphore` 限制并发，并配合 `tenacity` 进行重试，具备良好的系统弹性。
3.  **双写一致性 (Consistency)**:
    - `DualWriter` 实现了 ClickHouse 和 MySQL 的并行双写，并能处理部分失败的情况，确保了数据的冗余备份与高性能读取。
4.  **资源管理 (Resource Management)**:
    - 广泛使用了 `lifespan` 控制器和 `try...finally` 块进行资源回收，符合 Python 异步编程的最佳实践。

---

## 🔴 关键风险 (Critical Risks)

### 1. 安全性：环境变量硬编码 (Security: Hardcoded Credentials)
- **发现**: `services/stock-data/.env` 和 `services/task-scheduler/.env` 中包含真实的腾讯云 MySQL 密码 (`alwaysup@888`)。
- **影响**: 严重安全隐患。密码被检入版本控制系统。
- **建议**: **立即移除密码**。使用 `.env.example` 模板，并通过环境变量（如 Nacos 或 Docker Secrets）动态注入秘密。

### 2. 性能：缺乏分块/批量评估 (Performance: Lack of Vectorization)
- **发现**: `ScannerEngine` 对股票池进行分块 (`chunk_size=200`)，但在 `evaluate_stock` 中依然对每只股票循环调用 `strategy.evaluate`。
- **违规项**: 违反了 `quant-strategy` 标准中的 "Vectorization: Use Numpy/Pandas vectorized operations for all calculations. NEVER use Python loops for numerical computations."
- **影响**: 随着股票池扩大（如全市场 5000+ 只股票），Python 原生循环的开销将显著增加，无法发挥 NumPy/Pandas 的并行优势。
- **建议**: 优化 `BaseStrategy` 接口，增加 `evaluate_batch(self, df: pd.DataFrame)` 方法，在引擎层面一次性处理整个 chunk。

### 3. 并发冲突：ScannerEngine 实例状态 (Race Condition in Engine)
- **发现**: `ScannerEngine` 的 `_results` 和 `_errors` 是实例变量，且没有互斥保护。
- **影响**: 如果同一个 `ScannerEngine` 实例并发运行多个 `run_daily_scan` 任务，结果和错误列表会发生交叉污染。
- **建议**: 将结果集作为局部变量在任务方法中管理，或为实例变量添加锁。

---

## 🟡 改进建议 (Recommendations)

1.  **代码清理**: 根目录下存在大量未跟踪的脚本文件（如 `check_mysql.py`, `debug_data.py` 等），建议清理或移入 `scripts/` 目录并添加 `.gitignore`。
2.  **环境适配**: `get-stockdata/src/main.py` 中存在 `os.environ` 的强制硬编码值（如 `127.0.0.1:36301`）。这对于开发调试方便，但在容器化部署中可能导致不可预知的行为。建议通过配置中心（Nacos）统一管理。
3.  **数据校验增强 (已完成)**: 在 `DataSourceCollector` 中，已引入 `_validate_data_integrity` 方法，通过向量化操作校验价格非负、成交量非负以及 OHLC 逻辑一致性。

---

## 📝 结论 (Conclusion)

本次提交的代码在**微服务设计**和**异步并发处理**上表现出色，达到了工程化交付的水平。但在**计算性能优化（向量化）**和**代码安全性（身份凭证保护）**方面仍有显著提升空间。

**质控结论**: ⚠️ **部分通过 (Conditional Pass)**
> 请在合入主分支前修复环境变量硬编码问题，并评估策略引擎向量化重构的优先级。
