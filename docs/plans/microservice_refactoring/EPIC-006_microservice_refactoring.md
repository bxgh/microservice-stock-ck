# EPIC-006: Data Source Microservice Refactoring

## 目标
将 `get-stockdata` 单体服务拆分为独立的微服务架构 (`data-api` + 多个 `data-source` 服务)，解决网络环境复杂、连接异构、部署限制等问题，并为未来扩展打下基础。

## 关键成果 (Key Results)
1.  **架构解耦**：实现 1 个 `data-api` 聚合服务和 3 个独立的数据源服务 (`mootdx`, `akshare`, `baostock`)。
2.  **网络隔离**：各数据源服务独立配置 HTTP 代理环境，互不干扰。
3.  **统一接口**：基于 gRPC 定义标准化的 `DataSourceService` 接口。
4.  **同机部署**：所有服务在 `192.168.151.41` 上通过 Docker Compose 编排运行，使用 `network_mode: host`。
5.  **业务连续性**：重构过程中 API 保持可用，逐步切换底层实现。

---

## Story 列表与规划

### Story 6.1: 基础设施与接口定义 (Foundation)
**目标**：建立 gRPC 基础结构，定义数据交互协议，并集成到构建流程中。

*   **Task 6.1.1**: 定义 `proto/data_source.proto`，包含 `DataType`, `DataRequest`, `DataResponse` 定义。
*   **Task 6.1.2**: 配置 gRPC 代码生成工具 (protoc) 和 Python 依赖 (`grpcio-tools`)。
*   **Task 6.1.3**: 创建 `libs/common` 目录，存放生成的 Python gRPC 代码，供所有新服务复用。
*   **Task 6.1.4**: 规划全新项目目录结构，为新服务 (`services/mootdx-source`, `services/data-api` 等) 建立独立目录，不干扰现有服务。

### Story 6.2: 抽取 MooTDX 服务 (Pilot Phase)
**目标**：作为第一个试点，将最核心的 MooTDX 数据源独立出来的微服务。

*   **Task 6.2.1**: 创建 `services/mootdx-source` 项目结构与 Dockerfile。
*   **Task 6.2.2**: 迁移 `MootdxProvider` 核心逻辑到新服务，并实现 gRPC Server 端。
*   **Task 6.2.3**: 在 `data-api` (原 `get-stockdata`) 中实现 `GrpcMootdxClient`，替代本地 Provider。
*   **Task 6.2.4**: 调整 Docker Compose，加入 `mootdx-source` 服务，配置 Nacos 注册。
*   **Task 6.2.5**: 验证实时行情和分笔数据接口可用性。

### Story 6.3: 抽取 AkShare 服务 (Explicit Proxy)
**目标**：将依赖 Remote API 的 AkShare 数据源独立，解决最为棘手的代理配置问题。

*   **Task 6.3.1**: 创建 `services/akshare-source` 项目结构。
*   **Task 6.3.2**: 迁移 `AkshareProvider` (Remote API Client) 逻辑到新服务。
*   **Task 6.3.3**: 为 `akshare-source` 容器配置显式环境变量 `HTTP_PROXY=http://192.168.151.18:3128`。
*   **Task 6.3.4**: 实现 gRPC 接口，支持排行榜、财务、估值数据获取。
*   **Task 6.3.5**: 验证通过代理访问腾讯云 API 的连通性。

### Story 6.4: 抽取 BaoStock 服务与收尾 (Completion)
**目标**：完成最后一个数据源的拆分，并清理 `data-api` 中的遗留代码。

*   **Task 6.4.1**: 创建 `services/baostock-source` 项目结构。
*   **Task 6.4.2**: 迁移 `BaostockProvider`，配置 Squid 代理环境。
*   **Task 6.4.3**: 在 `data-api` 中完善 `DataSourceGateway`，实现基于 Nacos 的服务发现和自动降级路由。
*   **Task 6.4.4**: **清理**：移除 `data-api` 中原本的 `data_sources/providers` 本地实现代码。
*   **Task 6.4.5**: 全面回归测试，验证所有 API 端点。

---

## 风险管理

| 风险点 | 缓解措施 |
|--------|----------|
| **gRPC 序列化开销** | 传输大数据（如分笔）时使用 Bytes 传输 JSON/CSV 原始数据，避免对象反序列化开销。 |
| **调试复杂度增加** | 增加 `request_id` 全链路追踪日志；保留本地调用模式的配置开关用于开发环境。 |
| **Nacos 依赖风险** | `data-api` 增加本地配置兜底机制，若 Nacos 不可用可回退到硬编码 IP。 |
