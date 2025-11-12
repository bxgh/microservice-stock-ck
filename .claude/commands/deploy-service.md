# 微服务部署命令

一键部署微服务到不同环境，支持开发、测试和生产环境。

## 命令

```bash
# 部署到开发环境
/deploy-service task-scheduler dev

# 部署到测试环境
/deploy-service stock-data test

# 部署到生产环境
/deploy-service api-gateway prod

# 部署所有服务
/deploy-service all dev

# 回滚服务
/deploy-service task-scheduler rollback

# 查看部署状态
/deploy-service status
```

## 部署环境

### 开发环境 (dev)
- **目的**: 开发人员日常测试
- **配置**: 最小资源，快速启动
- **数据库**: SQLite 或开发数据库
- **日志**: DEBUG 级别
- **监控**: 基础健康检查

### 测试环境 (test)
- **目的**: 集成测试和QA验证
- **配置**: 模拟生产环境
- **数据库**: 独立测试数据库
- **日志**: INFO 级别
- **监控**: 完整监控指标

### 生产环境 (prod)
- **目的**: 正式运行环境
- **配置**: 高可用，性能优化
- **数据库**: 生产数据库集群
- **日志**: WARN 级别
- **监控**: 全面监控告警

## 部署流程

### 1. 部署前检查
```bash
# 验证代码质量
/deploy-service check task-scheduler

# 运行测试
/deploy-service test task-scheduler

# 检查依赖
/deploy-service dependencies task-scheduler

# 验证配置
/deploy-service validate task-scheduler
```

### 2. 构建镜像
```bash
# 构建 Docker 镜像
docker build -t task-scheduler:v1.0.0 ./task-scheduler

# 推送到镜像仓库
docker push registry.example.com/task-scheduler:v1.0.0
```

### 3. 环境配置
根据目标环境自动配置：
- **开发环境**: 环境变量从 `.env.dev`
- **测试环境**: 环境变量从 `.env.test`
- **生产环境**: 环境变量从 `.env.prod`

### 4. 服务部署
```bash
# 更新部署配置
kubectl apply -f k8s/task-scheduler-deployment.yaml

# 等待部署完成
kubectl rollout status deployment/task-scheduler

# 验证部署状态
kubectl get pods -l app=task-scheduler
```

### 5. 健康检查
```bash
# 检查服务健康状态
curl http://task-service:8080/api/v1/health

# 检查服务注册
curl http://nacos:8848/nacos/v1/ns/instance/list\?serviceName\=task-scheduler
```

## 部署配置

### Docker Compose 部署
适用于开发环境和简单部署：
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  task-scheduler:
    build: ./task-scheduler
    environment:
      - ENV=development
      - LOG_LEVEL=debug
    ports:
      - "8080:8080"
    depends_on:
      - nacos
      - mysql
```

### Kubernetes 部署
适用于生产环境：
```yaml
# k8s/task-scheduler-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: task-scheduler
spec:
  replicas: 3
  selector:
    matchLabels:
      app: task-scheduler
  template:
    metadata:
      labels:
        app: task-scheduler
    spec:
      containers:
      - name: task-scheduler
        image: task-scheduler:v1.0.0
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8080
          initialDelaySeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/ready
            port: 8080
          initialDelaySeconds: 5
```

## 部署策略

### 滚动更新
适用于生产环境，零停机部署：
```bash
# 滚动更新
kubectl set image deployment/task-scheduler task-scheduler=v1.1.0

# 监控更新进度
kubectl rollout status deployment/task-scheduler

# 回滚到上一版本
kubectl rollout undo deployment/task-scheduler
```

### 蓝绿部署
适用于关键服务，快速回滚：
```bash
# 部署绿色环境
kubectl apply -f k8s/task-scheduler-green.yaml

# 切换流量
kubectl patch service task-scheduler -p '{"spec":{"selector":{"version":"green"}}}'

# 验证后删除蓝色环境
kubectl delete -f k8s/task-scheduler-blue.yaml
```

### 金丝雀发布
适用于渐进式发布：
```bash
# 10% 流量到新版本
kubectl patch deployment task-scheduler -p '{"spec":{"template":{"spec":{"containers":[{"name":"task-scheduler","image":"v1.1.0"}]},"replicas":10}}'

# 逐步增加流量
# 50% -> 100%
```

## 部署监控

### 实时监控
```bash
# 查看部署状态
/deploy-service status task-scheduler

# 查看服务日志
/deploy-service logs task-scheduler

# 监控资源使用
/deploy-service metrics task-scheduler
```

### 告警配置
```yaml
# alerts/deployment-alerts.yaml
groups:
- name: deployment
  rules:
  - alert: ServiceDown
    expr: up{job="task-scheduler"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service {{ $labels.job }} is down"
```

## 回滚策略

### 自动回滚
当检测到以下情况时自动回滚：
- 健康检查失败超过阈值
- 错误率超过设定值
- 响应时间过长
- 资源使用异常

### 手动回滚
```bash
# 回滚到上一版本
/deploy-service task-scheduler rollback

# 回滚到指定版本
/deploy-service task-scheduler rollback v1.0.0

# 查看回滚历史
/deploy-service task-scheduler history
```

## 部署最佳实践

### 1. 版本管理
- 使用语义化版本号
- 每次部署打标签
- 保留历史版本镜像

### 2. 配置管理
- 环境配置外部化
- 敏感信息使用 Secrets
- 配置文件版本控制

### 3. 安全考虑
- 镜像安全扫描
- 网络策略配置
- 访问权限控制

### 4. 性能优化
- 镜像大小优化
- 启动时间优化
- 资源限制配置

## 示例输出

```
🚀 开始部署: task-scheduler -> dev
===============================

✅ 部署前检查通过
- 代码质量: OK
- 单元测试: 15/15 passed
- 配置验证: OK

📦 构建镜像: task-scheduler:v1.0.1-dev
- 构建时间: 2m 30s
- 镜像大小: 156MB

🌐 部署到开发环境
- 环境配置: 加载完成
- 服务启动: 30s
- 健康检查: OK

🔗 验证部署
- 服务地址: http://dev-task-scheduler:8080
- API 文档: http://dev-task-scheduler:8080/docs
- 健康状态: ✅ healthy

📊 部署统计
- 部署时间: 3m 45s
- 停机时间: 0s
- 回滚次数: 0

🎉 部署成功！
```

这个命令让微服务部署变得标准化、自动化且安全可靠！