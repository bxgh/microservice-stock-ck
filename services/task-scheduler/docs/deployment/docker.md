# Docker部署指南

## 🐳 容器化架构

### 镜像设计
- **基础镜像**: python:3.12-slim
- **运行时用户**: 非root用户
- **工作目录**: /app
- **暴露端口**: 8080

### 服务组件
- **taskscheduler**: 主应用服务
- **redis**: 缓存和消息队列
- **prometheus**: 监控数据收集
- **grafana**: 监控可视化

## 📋 部署配置

### 单机部署
```yaml
version: '3.8'
services:
  taskscheduler:
    build: .
    ports:
      - "8080:8080"
    environment:
      - TS_API_KEY=your-key
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

### 生产环境部署
```yaml
version: '3.8'
services:
  taskscheduler:
    image: taskscheduler:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
    environment:
      - TS_API_KEY=${API_KEY}
    volumes:
      - taskscheduler_data:/app/data
      - taskscheduler_logs:/app/logs

  redis:
    image: redis:7-alpine
    deploy:
      resources:
        limits:
          memory: 256M
    volumes:
      - redis_data:/data

volumes:
  taskscheduler_data:
  taskscheduler_logs:
  redis_data:
```

## 🔧 配置管理

### 环境变量配置
```bash
# 服务配置
TS_HOST=0.0.0.0
TS_PORT=8080
TS_DEBUG=false

# 安全配置
TS_API_KEY=your-secret-api-key

# 数据库配置
TS_DATABASE_PATH=data/taskscheduler.db

# Redis配置
TS_REDIS_URL=redis://redis:6379

# 日志配置
TS_LOG_LEVEL=INFO
TS_LOG_FILE=logs/taskscheduler.log
```

### 配置文件挂载
```yaml
volumes:
  - ./config:/app/config:ro
  - ./data:/app/data
  - ./logs:/app/logs
```

## 📊 监控配置

### Prometheus配置
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'taskscheduler'
    static_configs:
      - targets: ['taskscheduler:8080']
    metrics_path: '/api/v1/metrics'
```

### 健康检查
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## 🚀 部署脚本

### 构建镜像
```bash
docker build -t taskscheduler:latest .
```

### 启动服务
```bash
# 基础服务
docker-compose up -d

# 包含监控
docker-compose --profile monitoring up -d
```

### 扩展服务
```bash
# 扩展到3个实例
docker-compose up -d --scale taskscheduler=3
```

## 🔍 日志管理

### 日志输出
- 应用日志输出到stdout
- Docker收集容器日志
- 支持日志文件挂载

### 日志轮转
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 日志查看
```bash
# 实时日志
docker-compose logs -f taskscheduler

# 最近日志
docker-compose logs --tail=100 taskscheduler
```

## 🔒 安全配置

### 用户权限
```dockerfile
RUN groupadd -r taskscheduler && \
    useradd -r -g taskscheduler -d /app taskscheduler
USER taskscheduler
```

### 网络隔离
```yaml
networks:
  taskscheduler-net:
    driver: bridge
    internal: false
```

### 资源限制
```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 512M
```

## 📈 性能优化

### 镜像优化
- 使用多阶段构建
- 减少镜像层数
- 清理构建缓存

### 运行时优化
- 调整进程数量
- 优化内存使用
- 配置连接池

### 存储优化
- 使用SSD存储
- 配置数据卷
- 定期清理日志

## 🔄 更新部署

### 滚动更新
```bash
# 构建新镜像
docker build -t taskscheduler:v2 .

# 滚动更新
docker-compose up -d --no-deps taskscheduler
```

### 版本回滚
```bash
# 回滚到上一个版本
docker-compose up -d --no-deps taskscheduler:v1
```

### 数据迁移
```bash
# 备份数据
docker-compose exec taskscheduler cp -r /app/data ./backup/

# 恢复数据
docker-compose exec taskscheduler cp -r ./backup/ /app/data/
```

## 🛠️ 故障排查

### 容器状态
```bash
# 查看容器状态
docker-compose ps

# 查看容器详情
docker inspect taskscheduler-service
```

### 资源使用
```bash
# 查看资源使用
docker stats taskscheduler-service

# 查看容器内进程
docker-compose exec taskscheduler ps aux
```

### 网络连通
```bash
# 测试端口连通
docker-compose exec taskscheduler netstat -tuln

# 测试DNS解析
docker-compose exec taskscheduler nslookup redis
```

Docker部署提供了标准化、可复制的部署方案，适合不同规模的生产环境。