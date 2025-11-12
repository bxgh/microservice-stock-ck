# 项目源码树结构

## 📋 文档信息

- **文档版本**: v1.0
- **创建日期**: 2025-11-05
- **作者**: Winston (Architect Agent)
- **适用范围**: 股票数据分析系统
- **最后更新**: 2025-11-05

---

## 🎯 概述

本文档定义了股票数据分析系统的完整目录结构和文件组织规范。采用分层架构的目录组织方式，确保代码的可维护性、可读性和可扩展性。

---

## 📂 完整目录结构

```
fenbiDemo/
├── README.md                         # 项目说明文档
├── requirements.txt                  # Python依赖包列表
├── requirements-dev.txt              # 开发环境依赖包
├── pyproject.toml                    # 项目配置文件
├── .gitignore                        # Git忽略文件配置
├── .env.example                      # 环境变量示例文件
├── Dockerfile                        # Docker镜像构建文件
├── docker-compose.yml               # Docker Compose配置
├── docker-compose.prod.yml          # 生产环境Docker配置
├── Makefile                          # 项目构建和部署脚本
│
├── src/                              # 源代码主目录
│   ├── __init__.py
│   ├── main.py                       # 应用入口文件
│   ├── settings.py                   # 全局设置配置
│   │
│   ├── core/                         # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── config/                   # 配置管理
│   │   │   ├── __init__.py
│   │   │   ├── manager.py            # 配置管理器
│   │   │   ├── validator.py          # 配置验证器
│   │   │   └── settings.py           # 配置定义
│   │   │
│   │   ├── exceptions/               # 异常定义
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # 基础异常类
│   │   │   ├── data_source.py        # 数据源异常
│   │   │   ├── cache.py              # 缓存异常
│   │   │   └── validation.py         # 验证异常
│   │   │
│   │   ├── logging/                  # 日志管理
│   │   │   ├── __init__.py
│   │   │   ├── logger.py             # 结构化日志记录器
│   │   │   ├── formatters.py         # 日志格式化器
│   │   │   └── handlers.py           # 日志处理器
│   │   │
│   │   └── monitoring/               # 监控管理
│   │       ├── __init__.py
│   │       ├── metrics.py            # 指标收集器
│   │       ├── decorators.py         # 监控装饰器
│   │       └── health.py             # 健康检查
│   │
│   ├── domain/                       # 领域层
│   │   ├── __init__.py
│   │   ├── models/                   # 领域模型
│   │   │   ├── __init__.py
│   │   │   ├── stock.py              # 股票相关模型
│   │   │   ├── quote.py              # 行情数据模型
│   │   │   ├── tick.py               # 分笔数据模型
│   │   │   └── analysis.py           # 分析结果模型
│   │   │
│   │   ├── services/                 # 领域服务
│   │   │   ├── __init__.py
│   │   │   ├── volume_analysis.py    # 成交量分析服务
│   │   │   ├── temporal_analysis.py  # 时间模式分析服务
│   │   │   └── participant_analysis.py # 参与者行为分析服务
│   │   │
│   │   └── repositories/             # 领域仓储接口
│   │       ├── __init__.py
│   │       ├── data_repository.py    # 数据仓储接口
│   │       └── cache_repository.py   # 缓存仓储接口
│   │
│   ├── application/                  # 应用服务层
│   │   ├── __init__.py
│   │   ├── services/                 # 应用服务
│   │   │   ├── __init__.py
│   │   │   ├── data_acquisition.py   # 数据获取服务
│   │   │   ├── data_analysis.py      # 数据分析服务
│   │   │   ├── cache_service.py      # 缓存服务
│   │   │   └── batch_processor.py    # 批量处理器
│   │   │
│   │   ├── commands/                 # 命令处理器
│   │   │   ├── __init__.py
│   │   │   ├── get_quotes.py         # 获取行情命令
│   │   │   ├── get_ticks.py          # 获取分笔命令
│   │   │   └── analyze_data.py       # 分析数据命令
│   │   │
│   │   └── dto/                      # 数据传输对象
│   │       ├── __init__.py
│   │       ├── quote_dto.py          # 行情数据DTO
│   │       ├── tick_dto.py           # 分笔数据DTO
│   │       └── analysis_dto.py       # 分析结果DTO
│   │
│   ├── infrastructure/               # 基础设施层
│   │   ├── __init__.py
│   │   ├── adapters/                 # 适配器
│   │   │   ├── __init__.py
│   │   │   ├── data_sources/         # 数据源适配器
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py           # 数据源基类
│   │   │   │   ├── mootdx_adapter.py # Mootdx适配器
│   │   │   │   └── tushare_adapter.py # Tushare适配器(预留)
│   │   │   │
│   │   │   ├── cache/                # 缓存适配器
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py           # 缓存基类
│   │   │   │   ├── redis_cache.py    # Redis缓存适配器
│   │   │   │   └── memory_cache.py   # 内存缓存适配器
│   │   │   │
│   │   │   └── storage/              # 存储适配器
│   │   │       ├── __init__.py
│   │   │       ├── base.py           # 存储基类
│   │   │       ├── file_storage.py   # 文件存储适配器
│   │   │       └── database_storage.py # 数据库存储适配器
│   │   │
│   │   ├── repositories/             # 仓储实现
│   │   │   ├── __init__.py
│   │   │   ├── stock_data_repository.py # 股票数据仓储实现
│   │   │   └── cache_repository.py   # 缓存仓储实现
│   │   │
│   │   ├── external/                 # 外部服务
│   │   │   ├── __init__.py
│   │   │   ├── mootdx_client.py      # Mootdx客户端
│   │   │   └── notification_service.py # 通知服务
│   │   │
│   │   └── utils/                    # 基础设施工具
│   │       ├── __init__.py
│   │       ├── datetime_utils.py     # 时间工具
│   │       ├── validation_utils.py   # 验证工具
│   │       └── retry_utils.py        # 重试工具
│   │
│   ├── interfaces/                   # 接口层
│   │   ├── __init__.py
│   │   ├── api/                      # REST API
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # FastAPI应用入口
│   │   │   ├── dependencies.py       # 依赖注入
│   │   │   ├── middleware.py         # 中间件
│   │   │   │
│   │   │   └── v1/                   # API版本1
│   │   │       ├── __init__.py
│   │   │       ├── router.py         # 主路由
│   │   │       ├── quotes.py         # 行情接口
│   │   │       ├── ticks.py          # 分笔接口
│   │   │       ├── analysis.py       # 分析接口
│   │   │       └── health.py         # 健康检查接口
│   │   │
│   │   ├── cli/                      # 命令行接口
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # CLI主入口
│   │   │   ├── commands/             # CLI命令
│   │   │   │   ├── __init__.py
│   │   │   │   ├── quotes.py         # 行情命令
│   │   │   │   ├── ticks.py          # 分笔命令
│   │   │   │   └── analysis.py       # 分析命令
│   │   │   │
│   │   │   └── utils/                # CLI工具
│   │   │       ├── __init__.py
│   │   │       ├── formatter.py      # 输出格式化
│   │   │       └── config.py         # CLI配置
│   │   │
│   │   └── websocket/                # WebSocket接口(预留)
│   │       ├── __init__.py
│   │       ├── main.py               # WebSocket入口
│   │       └── handlers.py           # 消息处理器
│   │
│   └── shared/                       # 共享组件
│       ├── __init__.py
│       ├── constants/                # 常量定义
│       │   ├── __init__.py
│       │   ├── markets.py            # 市场常量
│       │   ├── data_types.py         # 数据类型常量
│       │   └── error_codes.py        # 错误码常量
│       │
│       ├── types/                    # 类型定义
│       │   ├── __init__.py
│       │   ├── common.py             # 通用类型
│       │   └── protocols.py          # 协议类型
│       │
│       └── utils/                    # 共享工具
│           ├── __init__.py
│           ├── decorators.py         # 装饰器
│           ├── helpers.py            # 辅助函数
│           └── validators.py         # 验证器
│
├── tests/                            # 测试目录
│   ├── __init__.py
│   ├── conftest.py                   # pytest配置
│   ├── fixtures/                     # 测试数据
│   │   ├── __init__.py
│   │   ├── quote_data.py            # 行情测试数据
│   │   ├── tick_data.py             # 分笔测试数据
│   │   └── market_data.py           # 市场测试数据
│   │
│   ├── unit/                         # 单元测试
│   │   ├── __init__.py
│   │   ├── test_config/              # 配置模块测试
│   │   ├── test_domain/              # 领域层测试
│   │   ├── test_application/         # 应用层测试
│   │   └── test_infrastructure/      # 基础设施层测试
│   │
│   ├── integration/                  # 集成测试
│   │   ├── __init__.py
│   │   ├── test_api/                 # API集成测试
│   │   ├── test_cli/                 # CLI集成测试
│   │   └── test_data_flow/           # 数据流集成测试
│   │
│   ├── e2e/                          # 端到端测试
│   │   ├── __init__.py
│   │   ├── test_scenarios/           # 业务场景测试
│   │   └── test_performance/         # 性能测试
│   │
│   └── utils/                        # 测试工具
│       ├── __init__.py
│       ├── factories.py              # 测试数据工厂
│       ├── mocks.py                  # Mock对象
│       └── helpers.py                # 测试辅助函数
│
├── config/                           # 配置文件目录
│   ├── settings.yaml                 # 主配置文件
│   ├── settings.dev.yaml             # 开发环境配置
│   ├── settings.test.yaml            # 测试环境配置
│   ├── settings.prod.yaml            # 生产环境配置
│   ├── logging.yaml                  # 日志配置
│   └── monitoring.yaml               # 监控配置
│
├── scripts/                          # 脚本目录
│   ├── setup.sh                     # 环境设置脚本
│   ├── build.sh                     # 构建脚本
│   ├── deploy.sh                    # 部署脚本
│   ├── backup.sh                    # 备份脚本
│   ├── migration/                    # 数据迁移脚本
│   │   ├── migrate_v1_to_v2.py
│   │   └── rollback_v2_to_v1.py
│   │
│   └── maintenance/                  # 维护脚本
│       ├── cleanup_logs.sh
│       ├── update_dependencies.sh
│       └── health_check.sh
│
├── docs/                             # 文档目录
│   ├── README.md                     # 文档首页
│   ├── architecture/                 # 架构文档
│   │   ├── optimized-architecture.md # 优化架构文档
│   │   ├── implementation-plan.md    # 实施计划
│   │   ├── standard-architecture-template.md # 标准架构模板
│   │   ├── source-tree.md           # 源码树文档
│   │   └── coding-standards.md      # 编码规范文档
│   │
│   ├── api/                          # API文档
│   │   ├── openapi.yaml             # OpenAPI规范
│   │   └── postman_collection.json  # Postman集合
│   │
│   ├── deployment/                   # 部署文档
│   │   ├── docker.md                # Docker部署指南
│   │   ├── kubernetes.md            # K8s部署指南
│   │   └── monitoring.md            # 监控配置指南
│   │
│   └── development/                  # 开发文档
│       ├── getting-started.md       # 快速开始
│       ├── testing.md               # 测试指南
│       └── troubleshooting.md       # 故障排查
│
├── monitoring/                       # 监控配置
│   ├── prometheus/                   # Prometheus配置
│   │   ├── prometheus.yml           # Prometheus主配置
│   │   ├── alert_rules.yml         # 告警规则
│   │   └── targets/                 # 监控目标配置
│   │
│   ├── grafana/                      # Grafana配置
│   │   ├── dashboards/              # 仪表板配置
│   │   └── provisioning/            # 自动配置
│   │
│   └── alertmanager/                # 告警管理配置
│       └── alertmanager.yml        # 告警路由配置
│
├── deployment/                       # 部署配置
│   ├── docker/                       # Docker相关配置
│   │   ├── Dockerfile               # 应用镜像
│   │   ├── Dockerfile.prod          # 生产环境镜像
│   │   └── docker-entrypoint.sh     # 容器启动脚本
│   │
│   ├── kubernetes/                   # K8s配置
│   │   ├── namespace.yaml           # 命名空间
│   │   ├── deployment.yaml          # 部署配置
│   │   ├── service.yaml             # 服务配置
│   │   ├── ingress.yaml             # 入口配置
│   │   └── configmap.yaml           # 配置映射
│   │
│   ├── nginx/                        # Nginx配置
│   │   ├── nginx.conf               # 主配置文件
│   │   ├── ssl/                     # SSL证书
│   │   └── sites-available/         # 站点配置
│   │
│   └── systemd/                      # 系统服务配置
│       └── stock-analysis.service   # 系统服务文件
│
├── data/                             # 数据目录
│   ├── cache/                        # 缓存数据
│   ├── logs/                         # 日志文件
│   ├── exports/                      # 导出文件
│   └── temp/                         # 临时文件
│
├── .github/                          # GitHub配置
│   ├── workflows/                    # GitHub Actions工作流
│   │   ├── ci.yml                   # 持续集成
│   │   ├── cd.yml                   # 持续部署
│   │   └── security.yml             # 安全扫描
│   │
│   ├── ISSUE_TEMPLATE/              # Issue模板
│   └── PULL_REQUEST_TEMPLATE.md     # PR模板
│
├── .bmad-core/                       # BMAD框架配置
│   ├── core-config.yaml             # 核心配置
│   ├── checklists/                   # 检查清单
│   ├── tasks/                        # 任务定义
│   ├── templates/                    # 模板文件
│   └── data/                         # 数据文件
│
├── .claude/                          # Claude配置
│   └── skills/                       # 技能配置
│
├── mootdx_api_examples/              # 原有示例项目(保留)
│   ├── README.md
│   ├── requirements.txt
│   ├── examples/
│   ├── tests/
│   └── utils/
│
├── venv/                             # Python虚拟环境
├── __pycache__/                      # Python字节码缓存
├── .pytest_cache/                    # pytest缓存
├── .coverage                         # 测试覆盖率文件
├── dist/                             # 构建产物
└── .DS_Store                         # macOS系统文件
```

---

## 📁 目录说明

### 🏗️ 核心架构层

#### `/src/core/` - 核心基础模块
**职责**: 提供系统级的基础服务和工具

- `config/` - 统一的配置管理
- `exceptions/` - 系统异常定义
- `logging/` - 结构化日志系统
- `monitoring/` - 监控和指标收集

#### `/src/domain/` - 领域层
**职责**: 包含核心业务逻辑和领域模型

- `models/` - 领域模型定义
- `services/` - 领域服务
- `repositories/` - 仓储接口定义

#### `/src/application/` - 应用服务层
**职责**: 协调领域对象完成应用程序功能

- `services/` - 应用服务实现
- `commands/` - 命令处理器
- `dto/` - 数据传输对象

#### `/src/infrastructure/` - 基础设施层
**职责**: 提供技术实现和外部系统集成

- `adapters/` - 外部系统适配器
- `repositories/` - 仓储实现
- `external/` - 外部服务客户端
- `utils/` - 基础设施工具

#### `/src/interfaces/` - 接口层
**职责**: 处理用户交互和外部接口

- `api/` - REST API接口
- `cli/` - 命令行接口
- `websocket/` - WebSocket接口(预留)

### 🧪 测试架构

#### `/tests/unit/` - 单元测试
**职责**: 测试单个组件的功能

- `test_config/` - 配置模块测试
- `test_domain/` - 领域层测试
- `test_application/` - 应用层测试
- `test_infrastructure/` - 基础设施层测试

#### `/tests/integration/` - 集成测试
**职责**: 测试组件间的交互

- `test_api/` - API集成测试
- `test_cli/` - CLI集成测试
- `test_data_flow/` - 数据流集成测试

#### `/tests/e2e/` - 端到端测试
**职责**: 测试完整的业务流程

- `test_scenarios/` - 业务场景测试
- `test_performance/` - 性能测试

### ⚙️ 配置和部署

#### `/config/` - 配置文件
**职责**: 环境配置管理

- `settings.yaml` - 主配置文件
- `settings.*.yaml` - 环境特定配置
- `logging.yaml` - 日志配置
- `monitoring.yaml` - 监控配置

#### `/deployment/` - 部署配置
**职责**: 不同环境的部署配置

- `docker/` - Docker容器配置
- `kubernetes/` - Kubernetes配置
- `nginx/` - 负载均衡配置
- `systemd/` - 系统服务配置

### 📊 监控和运维

#### `/monitoring/` - 监控配置
**职责**: 系统监控和告警配置

- `prometheus/` - Prometheus配置
- `grafana/` - Grafana仪表板
- `alertmanager/` - 告警管理配置

---

## 🔧 文件命名规范

### Python文件命名

| 类型 | 命名规范 | 示例 |
|------|----------|------|
| 模块文件 | `snake_case.py` | `data_acquisition.py` |
| 类文件 | `snake_case.py` | `quote_data.py` |
| 测试文件 | `test_*.py` | `test_data_acquisition.py` |
| 配置文件 | `kebab-case.yaml` | `settings.yaml` |
| 脚本文件 | `kebab-case.sh` | `deploy.sh` |

### 目录命名规范

| 类型 | 命名规范 | 示例 |
|------|----------|------|
| 源码目录 | `snake_case` | `data_sources/` |
| 配置目录 | `kebab-case` | `monitoring/` |
| 文档目录 | `kebab-case` | `architecture/` |

---

## 📝 新增文件指南

### 添加新的领域模型

1. 在 `src/domain/models/` 下创建模型文件
2. 在 `tests/unit/test_domain/` 下创建对应测试
3. 更新 `src/domain/models/__init__.py` 导出新模型
4. 如果需要API暴露，在 `src/interfaces/api/v1/` 下创建接口

### 添加新的应用服务

1. 在 `src/application/services/` 下创建服务文件
2. 在 `src/application/dto/` 下创建DTO文件
3. 在 `tests/unit/test_application/` 下创建测试
4. 在相应的接口层添加调用逻辑

### 添加新的数据源适配器

1. 在 `src/infrastructure/adapters/data_sources/` 下创建适配器
2. 继承 `base.py` 中的基类
3. 在配置文件中添加相应配置
4. 编写集成测试验证功能

---

## 🚀 模块导入规范

### 导入顺序

1. **标准库导入**
   ```python
   import os
   import sys
   from datetime import datetime
   ```

2. **第三方库导入**
   ```python
   import pandas as pd
   import numpy as np
   from fastapi import FastAPI
   ```

3. **本地模块导入**
   ```python
   from src.core.config.manager import ConfigManager
   from src.domain.models.quote import QuoteData
   from src.application.services.data_acquisition import DataAcquisitionService
   ```

### 相对导入规范

- 同层模块使用相对导入
- 跨层模块使用绝对导入
- 避免循环导入

---

## 📋 维护指南

### 目录结构维护

1. **定期清理**: 删除不再使用的文件和目录
2. **保持一致性**: 新增文件时遵循现有命名规范
3. **文档更新**: 结构变更时同步更新相关文档
4. **测试覆盖**: 新增模块时确保有对应测试

### 版本控制

1. **忽略文件**: 确保 `.gitignore` 包含所有应该忽略的文件
2. **分支策略**: 不同环境配置使用不同分支管理
3. **提交规范**: 遵循约定的提交信息格式

---

## 📖 相关文档

- [编码规范文档](coding-standards.md)
- [优化架构文档](optimized-architecture.md)
- [实施计划文档](implementation-plan.md)
- [API文档](../api/openapi.yaml)
- [部署指南](../deployment/docker.md)

---

**文档版本**: v1.0
**创建日期**: 2025-11-05
**最后更新**: 2025-11-05
**维护者**: Winston (Architect Agent)