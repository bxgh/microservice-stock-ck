# Task Scheduler 微服务部署指南

## 🚀 快速开始

### 前置条件

确保基础设施服务已启动：
```bash
# 从项目根目录
cd /home/bxgh/microservice-stock
docker-compose -f docker-compose.infrastructure.yml up -d
```

验证基础设施服务状态：
```bash
# 检查Nacos
curl http://localhost:8848/nacos/

# 检查Redis
timeout 3 bash -c "</dev/tcp/localhost/6379"

# 检查ClickHouse
curl http://localhost:8123/ping
```

### 部署方法

#### 使用部署脚本（推荐）

```bash
# 进入Task Scheduler目录
cd services/task-scheduler

# 一键部署（Docker Compose）
./deploy.sh deploy
```

#### 手动Docker Compose部署

```bash
cd services/task-scheduler

# 构建镜像（使用验证成功的方法）
docker run --name task-scheduler-builder \
    --network microservice-stock_microservice-stock \
    -e http_proxy=http://192.168.151.18:3128 \
    -e https_proxy=http://192.168.151.18:3128 \
    -v $(pwd)/app.py:/tmp/app.py \
    -v $(pwd)/requirements-heartbeat.txt:/tmp/requirements-heartbeat.txt \
    python:3.12-slim bash -c "
    mkdir -p /app &&
    pip install aiohttp -i https://pypi.tuna.tsinghua.edu.cn/simple &&
    cp /tmp/app.py /app/ &&
    echo '✅ 依赖安装和应用复制完成'
"

docker commit task-scheduler-builder task-scheduler:latest
docker rm task-scheduler-builder

# 启动服务
docker-compose up -d
```

## 📊 验证部署

### 自动验证
```bash
./deploy.sh verify
```

### 手动验证

1. **健康检查**
```bash
curl http://localhost:8081/health
```

2. **服务信息**
```bash
curl http://localhost:8081/info
```

3. **Nacos注册检查**
```bash
curl "http://localhost:8848/nacos/v1/ns/instance/list?serviceName=task-scheduler"
```

## 🔧 管理命令

```bash
# 部署服务（Docker Compose）
./deploy.sh deploy

# 重启服务
./deploy.sh restart

# 停止服务
./deploy.sh stop

# 查看日志
./deploy.sh logs

# 查看状态
./deploy.sh status

# 验证部署
./deploy.sh verify

# 显示帮助
./deploy.sh help
```

## 🌐 访问地址

- **Task Scheduler API**: http://localhost:8081
- **健康检查**: http://localhost:8081/health
- **服务信息**: http://localhost:8081/info
- **任务列表**: http://localhost:8081/tasks
- **Nacos控制台**: http://localhost:8848/nacos (nacos/nacos)

## 📋 服务特性

### 核心功能
- ✅ HTTP REST API
- ✅ 健康检查端点
- ✅ 服务信息端点
- ✅ Nacos服务注册与发现
- ✅ 心跳机制（5秒间隔）
- ✅ 优雅启动与关闭

### 基础设施集成
- ✅ Nacos（服务注册发现）
- ✅ Redis（缓存）
- ✅ ClickHouse（时序数据）
- ✅ RabbitMQ（消息队列）

## 🔍 故障排除

### 常见问题

1. **端口冲突**
   - 修改 `app_with_heartbeat.py` 中的端口配置
   - 默认使用端口 8081

2. **依赖缺失**
   ```bash
   sudo apt install -y python3-aiohttp python3-requests
   ```

3. **Nacos连接失败**
   - 检查Nacos是否运行：`curl http://localhost:8848/nacos/`
   - 确保在正确的网络环境中

4. **Docker部署问题**
   - 检查网络：`docker network ls | grep microservice`
   - 查看容器日志：`docker logs task-scheduler`

### 日志查看

```bash
# 查看应用日志
./deploy.sh logs

# 或直接查看
tail -f app.log
```

## 🏗️ 架构说明

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   HTTP Client   │────│ Task Scheduler│────│  Nacos Server   │
│  (8081:8081)    │    │ (Microservice)│    │   (8848)        │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
            ┌───────▼──┐ ┌─────▼────┐ ┌──▼──────┐
            │   Redis │ │ClickHouse│ │RabbitMQ│
            │ (6379)  │ │ (8123)   │ │(5672)  │
            └─────────┘ └──────────┘ └─────────┘
```

## 📈 监控

### 服务健康状态
- Nacos控制台：http://localhost:8848/nacos
- 健康检查API：http://localhost:8081/health

### 日志聚合
服务日志写入 `app.log`，可使用 `./deploy.sh logs` 实时查看。

## 🔄 开发环境

### 本地开发
```bash
# 安装开发依赖（如果需要）
pip install aiohttp requests

# 直接运行应用（不推荐生产环境）
python3 app.py
```

### 环境变量
```bash
# Nacos服务配置
export NACOS_SERVER_URL=http://nacos:8848
export SERVICE_NAME=task-scheduler
export SERVICE_GROUP=DEFAULT_GROUP
export SERVICE_PORT=8081

# 日志和心跳配置
export LOG_LEVEL=INFO
export HEARTBEAT_INTERVAL=30
```

## 📚 参考资料

- [Nacos官方文档](https://nacos.io/zh-cn/docs/what-is-nacos.html)
- [aiohttp文档](https://docs.aiohttp.org/)
- [FastAPI文档](https://fastapi.tiangolo.com/)

---

**注意**: 在生产环境部署前，请确保：
1. 修改默认密码
2. 配置HTTPS
3. 设置适当的资源限制
4. 配置备份策略
5. 设置监控告警