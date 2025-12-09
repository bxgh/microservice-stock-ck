# Tech Stack

基于微服务分层的完整架构，选择以下技术栈：

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **Frontend Language** | TypeScript | 5.0+ | 类型安全的 JavaScript | 提供类型安全，改善开发体验，与后端共享类型定义 |
| **Frontend Framework** | Vue 3 | 3.4+ | Web UI 管理界面 | 现代响应式框架，组合式API，性能优秀，适合管理界面开发 |
| **UI Component Library** | Element Plus | 2.4+ | UI 组件库 | Vue 3生态最完整的组件库，开箱即用的管理界面组件 |
| **State Management** | Pinia | 2.1+ | 前端状态管理 | Vue官方推荐状态管理，类型安全，简单易用 |
| **Build Tool** | Vite | 5.0+ | 前端构建工具 | 快速热更新，现代化构建工具，Vue原生支持 |
| **Router** | Vue Router | 4.2+ | 路由管理 | Vue官方路由库，与Vue 3完美集成 |
| **Backend Language** | Python | 3.11+ | 后端服务开发 | 成熟的异步支持，丰富的微服务生态 |
| **Backend Framework** | FastAPI | 0.104+ | API 服务框架 | 高性能异步框架，自动生成 OpenAPI 文档 |
| **API Style** | RESTful API | OpenAPI 3.0 | API 设计标准 | 标准化，工具支持好，易于理解和使用 |
| **Database** | MySQL | 5.7 (外部) | 元数据存储 | 稳定可靠，你已有的外部数据库 |
| **Cache** | Redis | 7.0+ | 缓存和消息队列 | 高性能，支持多种数据结构，适合消息队列 |
| **File Storage** | 本地文件系统 | - | 日志和临时文件 | 简化部署，避免外部依赖 |
| **Authentication** | 跳过 | - | API 认证 | 内网环境，个人使用，简化配置 |
| **Frontend Testing** | Vitest + Vue Test Utils | 1.0+ | 前端测试 | 快速，现代化，与 Vue 3 生态集成好 |
| **Backend Testing** | pytest | 7.4+ | 后端测试 | Python 标准测试框架，功能强大 |
| **E2E Testing** | Playwright | 1.40+ | 端到端测试 | 现代化，跨浏览器，可靠性高 |
| **Build Tool** | Docker | 24.0+ | 容器化构建 | 标准化构建环境，确保一致性 |
| **Frontend Apps** | frontend-web, task-scheduler-front | 1.0+ | 前端应用 | 企业级前端应用，Vue 3 + TypeScript + Element Plus |
| **IaC Tool** | Docker Compose | 2.20+ | 基础设施编排 | 简单易用，适合单机多服务部署 |
| **CI/CD** | GitHub Actions | - | 自动化部署（可选） | 与代码仓库集成，自动化测试和部署 |
| **Monitoring** | 轻量级日志 | JSON 格式 | 应用监控 | 简化运维，避免复杂监控系统 |
| **Logging** | Python logging | 结构化 JSON | 日志管理 | 标准库，结构化输出便于查询 |
| **CSS Framework** | Element Plus | 2.4+ | 样式框架 | 与 UI 组件库集成，Vue 3 设计一致性 |
