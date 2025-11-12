# External APIs

## External Database APIs

**Purpose:** 连接你已有的外部 MySQL 5.7 数据库进行元数据存储

**Documentation:** MySQL 5.7 官方文档
**Base URL(s):** `mysql://username:password@host:port/database`
**Authentication:** 用户名/密码认证
**Rate Limits:** 由数据库连接池配置决定

**Key Endpoints Used:**
- `SQL queries via SQLAlchemy ORM` - 任务配置和元数据 CRUD 操作

**Integration Notes:**
- 使用 SQLAlchemy 作为 ORM，提供数据库无关的抽象层
- 配置连接池避免连接泄漏
- 支持事务回滚确保数据一致性

## Proxy Configuration APIs

**Purpose:** 通过代理 192.168.151.18:3128 访问外部资源

**Documentation:** HTTP 代理协议标准
**Base URL(s):** 通过代理访问的所有外部请求
**Authentication:** 代理认证 (如需要)
**Rate Limits:** 代理服务器的限制

**Integration Notes:**
- 在 Python aiohttp 客户端中配置代理设置
- 支持代理认证 (用户名/密码)
- 实现代理连接池优化性能
