# Quant-Strategy 量化策略微服务

## 📋 概述

基于微服务模板创建的量化策略引擎服务，提供策略管理、信号生成与回测功能。

## 🎯 支持的策略类型

| 策略代码 | 策略名称 | 描述 |
|---------|---------|------|
| `ofi` | 主动买卖单失衡策略 | 基于Order Flow Imbalance分析多空力量 |
| `smart_money` | 大单资金流向追踪 | 识别主力资金吸筹/出货行为 |
| `order_book` | 盘口深度压力分析 | 分析五档盘口的委买委卖压力差 |
| `vwap` | 日内VWAP乖离策略 | 基于VWAP的均值回归/趋势确认 |
| `liquidity_shock` | 流动性冲击监控 | 监测交易对价格的冲击成本 |

## 🚀 快速开始

### 构建和启动

```bash
# 构建Docker镜像
docker build -t quant-strategy:latest .

# 启动服务
docker compose up -d

# 查看日志
docker logs quant-strategy
```

### 验证服务

```bash
# 健康检查
curl http://localhost:8084/api/v1/health

# API文档
open http://localhost:8084/docs
```

## 📁 项目结构

```
quant-strategy/
├── src/
│   ├── api/
│   │   ├── health_routes.py      # 健康检查
│   │   ├── strategy_routes.py    # 策略管理API
│   │   └── middleware.py         # 中间件
│   ├── config/
│   │   └── settings.py           # 应用配置
│   ├── models/
│   │   ├── base_models.py        # 基础模型
│   │   └── strategy_models.py    # 策略模型
│   ├── registry/
│   │   └── nacos_registry_simple.py
│   └── main.py                   # 入口
├── config/
│   └── quant-strategy.yaml       # 配置文件
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 🔧 API接口

### 策略管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/strategies/` | 获取策略列表 |
| GET | `/api/v1/strategies/{id}` | 获取策略详情 |
| POST | `/api/v1/strategies/` | 创建策略 |
| DELETE | `/api/v1/strategies/{id}` | 删除策略 |
| PUT | `/api/v1/strategies/{id}/toggle` | 启用/禁用策略 |

### 策略执行

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/strategies/{id}/backtest` | 回测策略 |
| GET | `/api/v1/strategies/{id}/signals` | 获取策略信号 |

### 健康检查

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/ready` | 就绪检查 |
| GET | `/api/v1/live` | 存活检查 |

## ⚙️ 配置

### 环境变量

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `QS_PORT` | 8084 | 服务端口 |
| `QS_LOG_LEVEL` | INFO | 日志级别 |
| `QS_STOCKDATA_SERVICE_URL` | http://get-stockdata:8080 | 数据源服务地址 |
| `QS_MAX_CONCURRENT_STRATEGIES` | 20 | 最大并发策略数 |

## 📊 后续开发计划

- [ ] 实现OFI策略计算引擎
- [ ] 实现Smart Money资金流向分析
- [ ] 实现盘口压力实时监控
- [ ] 实现VWAP计算与信号生成
- [ ] 实现流动性冲击检测
- [ ] 完善回测框架
- [ ] 添加WebSocket实时推送

## 📚 参考资源

- [策略设计文档](../get-stockdata/docs/design/stratege/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
