# 快速部署指南

## 🚀 一键部署

### 前置要求
- Docker 20.0+
- Docker Compose 2.0+
- 至少1GB可用内存
- 至少1GB可用磁盘空间

### 部署步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd microservice_component
   ```

2. **一键部署**
   ```bash
   python3 deploy.py deploy
   ```

3. **验证部署**
   ```bash
   curl http://localhost:8080/api/v1/health
   ```

## 📊 验证成功

### 服务状态检查
- API服务: http://localhost:8080
- 健康检查: http://localhost:8080/api/v1/health
- 服务统计: http://localhost:8080/api/v1/stats

### 管理界面
- API文档: http://localhost:8080/docs
- 监控面板: http://localhost:9090 (可选)
- 日志查看: `docker-compose logs taskscheduler`

## 🔧 配置选项

### 环境变量配置
```bash
# API配置
export TS_PORT=8080
export TS_API_KEY=your-secret-key

# 数据库配置
export TS_DATABASE_PATH=data/taskscheduler.db

# Redis配置
export TS_REDIS_URL=redis://redis:6379
```

### 配置文件修改
编辑 `config/taskscheduler.yaml`:
```yaml
service:
  name: "TaskScheduler"
  version: "2.0.0"

api:
  port: 8080
  access_log: true

security:
  api_key: "your-secret-key"
```

## 📦 部署模式

### 基础部署
- 单容器部署
- SQLite数据库
- 基础监控
- 适合开发和小规模使用

### 生产部署
- 多实例部署
- PostgreSQL数据库
- Redis集群
- 完整监控栈
- 高可用配置

### 监控部署
- 包含Prometheus
- 包含Grafana
- 完整告警配置
- 性能指标收集

## 🛠️ 常用操作

### 查看服务状态
```bash
docker-compose ps
```

### 查看服务日志
```bash
docker-compose logs taskscheduler
```

### 重启服务
```bash
docker-compose restart taskscheduler
```

### 停止服务
```bash
docker-compose down
```

### 清理数据
```bash
python3 deploy.py cleanup
```

## 🔍 故障排查

### 服务无法启动
1. 检查端口占用: `netstat -tuln | grep 8080`
2. 检查Docker状态: `docker version`
3. 查看启动日志: `docker-compose logs taskscheduler`

### 健康检查失败
1. 检查数据库连接
2. 验证配置文件
3. 查看错误日志

### 性能问题
1. 检查资源使用: `docker stats`
2. 调整并发配置
3. 优化数据库查询

## 📋 部署清单

### 开发环境
- [x] 快速启动
- [x] 热重载支持
- [x] 调试日志
- [x] 简化配置

### 测试环境
- [x] 数据持久化
- [x] 基础监控
- [x] 配置管理
- [x] 自动化部署

### 生产环境
- [x] 多实例部署
- [x] 数据备份
- [x] 监控告警
- [x] 负载均衡

## 📞 技术支持

- 查看在线文档: `/docs`
- 提交问题反馈: GitHub Issues
- 获取最新版本: GitHub Releases

部署完成后，您就可以开始使用TaskScheduler微服务组件了！