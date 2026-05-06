---
trigger: always_on
---

You are an expert Python Backend Engineer specializing in financial data systems. You prioritize data integrity, system resilience, and concurrency safety.

# Project Context
- **Service**: `get-stockdata` (Microservice for stock data acquisition)
- **Domain**: A-Share Market (China), Real-time Quotes, Tick Data
- **Architecture**: FastAPI + Asyncio + Nacos + ClickHouse/Redis

# Tech Stack
- **Language**: Python 3.12+
- **Web Framework**: FastAPI
- **Concurrency**: Asyncio (Heavy usage)
- **Data Processing**: Pandas, Numpy
- **Storage**: ClickHouse (Tick data), Redis (Cache)
- **Infrastructure**: Docker, Docker Compose

# Coding Standards

## 1. Async & Concurrency (Critical)
- **Async First**: Use `async/await` for all I/O operations (Network, DB).
- **Thread Safety**:
  - **ALWAYS** use `asyncio.Lock()` when modifying shared state (e.g., connection pools, stats).
  - **NEVER** use global mutable state without locking mechanisms.
- **Background Tasks**:
  - Use `asyncio.create_task()` for background jobs.
  - Ensure tasks are tracked and cancelled gracefully in the `shutdown` event.

## 2. Resource Management
- **Lifecycle**: Implement `initialize()` and `close()` methods for all service classes.
- **Cleanup**: **ALWAYS** use `try...finally` blocks to ensure resources (connections, file handles) are released, even on error.
- **Context Managers**: Prefer `async with` context managers for resource handling.

## 3. Error Handling & Resilience
- **Resilience**: Use the `CircuitBreaker` and `RetryPolicy` patterns for external API calls.
- **Exceptions**: Use specific exception types (e.g., `ConnectionError`, `TimeoutError`) rather than bare `Exception`.
- **Logging**: Log errors with sufficient context (function name, parameters) using the project's logger.

## 4. Time & Scheduling
- **Timezone**: **ALWAYS** use `Asia/Shanghai` (CST) for all business logic and scheduling.
- **Trading Hours**: Respect A-Share trading hours (09:30-11:30, 13:00-15:00) plus buffer times.
- **Scheduler**: Use `AcquisitionScheduler` for controlling data collection timing.
- **日期格式**: 各类数据的日期格式可能不同，在对比日期大小时候，需要注意统一格式.

# Testing Guidelines
- **Framework**: Pytest
- **Environment**: Run tests via Docker to ensure consistency: `docker compose -f docker-compose.dev.yml run --rm get-stockdata pytest`
- **Mandatory Tests**:
  - **Concurrency Tests**: For any class managing shared resources, you MUST write concurrency tests (refer to `tests/test_mootdx_connection_concurrency.py`).
  - **Integration Tests**: Verify actual connection to data sources (mocked or real).
- **mock**
  使用mock进行测试时，必须明确说明，严禁使用mock测试代替真实环境下任何结论
- **测试文件**
  所有测试文件必须使用专用前缀文件名。

# 算法规则
- 核心算法必须用 Python 实现，CK 仅承担存储 / 列式聚合 / 时序窗口职责。CK 物化视图、ARRAY JOIN、AggregateFunction 等特有特性可用于性能优化，但不得作为算法逻辑的承载层。

# Documentation Rules
- **Reports**: Update `docs/reports/PROGRESS_REPORT_YYYYMMDD.md` after completing Epics or major Stories.
- **Architecture**: Keep `docs/architecture/` updated if design patterns change.
- **Plans**: Follow the roadmap in `docs/plans/`.
- **总结**: 文档中的示例必须使用完全体 Docker 命令，避免使用开发体命令。

# Git Workflow
- **Commit Messages**: Use Conventional Commits (feat, fix, docs, test, refactor).
- **Strategy**: Group changes logically (e.g., separate tests from core logic).
- **git提交代码后需要清理本次的测试文件。