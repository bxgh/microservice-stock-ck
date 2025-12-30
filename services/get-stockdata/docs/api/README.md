# API 接口文档索引 (API Documentation Index)

本目录存储 `get-stockdata` 服务的所有详细接口文档。为了保持项目结构的整洁和知识的连续性，请遵循以下约定。

## 目录索引

| 文档名称 | 描述 | 最后更新 |
| :--- | :--- | :--- |
| [股票 K 线数据 API](stock_kline_api.md) | 包含日线查询、ClickHouse/MySQL 路由策略、同步接口及 Baostock 代理。 | 2025-12-30 |
| [腾讯云 Akshare 代理 API](tencent_akshare_api.md) | 包含财务数据、估值数据、人气榜单等内部代理接口说明。 | 2025-12-30 |

## 文档规范与保存策略 (Preservation Policy)

> [!IMPORTANT]
> **所有后续开发的新 API 接口文档，必须保存至本目录 (`/docs/api/`)。**

1.  **实证原则**：在编写文档前，必须验证 API 的真实端口（查阅 `docker-compose.dev.yml`）和路径（查阅路由代码或 `openapi.json`）。禁止基于通用常识进行猜测。
2.  **单一事实来源**：如果源码逻辑与文档不符，请先更新文档。文档应准确反映当前代码的实现（如复权参数、日期格式等）。
3.  **命名规范**：文件名请使用小写蛇形命名法（snake_case），例如 `new_feature_api.md`。
4.  **跨文件引用**：如果接口逻辑发生迁移或整合（如 K 线接口从 Akshare 迁移至独立文档），必须在原文档中留下清晰的重定向说明。

---
*由 AI 助手维护 - 最后更新: 2025-12-30*
