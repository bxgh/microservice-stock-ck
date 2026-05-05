# 数据质量与校验体系 (Data Quality & Validation)

本项目建立了多层级、全自动的数据校验体系，确保金融数据的完整性、一致性与准确性。

## 主题文档

### 1. [核心校验标准](standards.md)
定义了分笔数据 (Intraday/History)、K线数据、股票名单及全市场维度的具体校验阈值与规则。

### 2. [接口集成标准](api_integration.md)
规定了微服务间调用的响应契约 (ApiResponse)、Pydantic 模型校验以及具备重试能力的智能客户端 (BaseApiClient)。

### 3. [数据持久化标准](persistence.md)
详细说明了校验结果在 MySQL 中的 Schema 设计、`AuditRepository` 的事务处理逻辑以及查询示例。

### 4. [远程触发机制](trigger.md)
介绍了如何通过 Orchestrator API 远程触发实时数据审计，支持指定日期的数据对账。

## 体系架构

所有校验逻辑由 `libs/gsd-shared` 统一提供，由 `gsd-worker` 负责执行具体的审计 Job，并将结果通过 `AuditRepository` 持久化至腾讯云 MySQL 审计库，供前端监控看板调用。
