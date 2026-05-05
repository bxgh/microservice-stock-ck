# Unified Project Structure

```plaintext
microservice-stock/
├── .github/                        # CI/CD workflows
├── services/                       # 应用服务包
│   ├── api-gateway/                # API Gateway (Nginx)
│   ├── task-scheduler/             # 任务调度服务
│   ├── data-collector/             # 数据采集服务
│   ├── data-processor/             # 数据处理服务
│   ├── data-storage/               # 数据存储服务
│   ├── notification/               # 通知服务
│   ├── monitor/                    # 监控服务
│   └── web-ui/                     # Web UI 管理界面
├── packages/                       # 共享包
│   ├── shared/                     # 共享类型和工具
│   └── config/                     # 共享配置
├── infrastructure/                 # 基础设施定义
│   ├── docker-compose.yml          # 服务编排
│   ├── redis/                      # Redis 配置
│   ├── clickhouse/                 # ClickHouse 配置
│   └── nginx/                      # Nginx 配置
├── scripts/                        # 构建和部署脚本
├── docs/                           # 文档
├── tests/                          # 集成测试
├── .env.example                    # 环境变量模板
├── docker-compose.yml              # Docker Compose 主配置
└── README.md                       # 项目说明
```
