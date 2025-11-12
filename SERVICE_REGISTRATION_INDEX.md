# 微服务 Nacos 服务注册资源索引

## 📁 文档结构

本文档提供了微服务项目中 Nacos 服务注册相关的所有资源链接和快速导航。

## 🎯 核心文档

| 文档 | 描述 | 目标读者 |
|------|------|----------|
| [📋 实施指南](services/task-scheduler/NACOS_SERVICE_REGISTRATION.md) | 完整的 Nacos 服务注册实施指南 | 架构师、开发人员 |
| [⚡ 快速部署](services/task-scheduler/QUICK_DEPLOYMENT_GUIDE.md) | 5分钟快速集成指南 | 开发人员 |
| [🔧 代码模板](services/task-scheduler/nacos_registration_template.py) | 可直接复用的代码模板 | 开发人员 |

## 🚀 快速开始

### 新服务集成步骤

1. **复制模板**
   ```bash
   cp services/task-scheduler/nacos_registration_template.py your-service/nacos_registry.py
   pip install aiohttp
   ```

2. **快速配置**
   ```python
   from nacos_registry import initialize_nacos, register_to_nacos, cleanup_nacos

   # 启动时
   await initialize_nacos()
   await register_to_nacos("your-service", 8080, "FastAPI", "服务描述")

   # 关闭时
   await cleanup_nacos()
   ```

3. **环境变量**
   ```bash
   export NACOS_SERVER_URL=http://nacos:8848
   export SERVICE_NAME=your-service
   export SERVICE_PORT=8080
   ```

## 🏗️ 成功案例

### Task Scheduler 微服务

**状态**: ✅ 完全集成，生产就绪

**关键成果**:
- ✅ 自动服务注册
- ✅ 心跳机制（10秒间隔）
- ✅ IP地址自动获取
- ✅ 重试机制
- ✅ 优雅关闭

**访问地址**:
- 服务: http://localhost:8081
- 文档: http://localhost:8081/docs
- 健康检查: http://localhost:8081/health

**验证命令**:
```bash
# 检查服务注册
curl "http://localhost:8848/nacos/v1/ns/service/list"

# 检查实例详情
curl "http://localhost:8848/nacos/v1/ns/instance/list?serviceName=task-scheduler"

# 查看服务日志
docker logs task-scheduler-heartbeat-debug | grep -E "(注册|心跳)"
```

## 📋 已服务列表

### 当前已注册服务

| 服务名 | 端口 | 状态 | 注册时间 |
|--------|------|------|----------|
| task-scheduler | 8081 | ✅ 运行中 | 2025-11-12 |

### 检查命令
```bash
# 查看所有已注册服务
curl -s "http://localhost:8848/nacos/v1/ns/service/list" | jq

# 查看具体服务
curl -s "http://localhost:8848/nacos/v1/ns/instance/list?serviceName=SERVICE_NAME"
```

## 🔧 开发环境配置

### Nacos 访问信息

- **Web界面**: http://localhost:8848/nacos
- **用户名/密码**: nacos/nacos (如果启用)
- **API端点**: http://localhost:8848/nacos/v1

### Docker 网络

```bash
# 查看网络
docker network ls | grep microservice-stock

# 查看网络详情
docker network inspect microservice-stock_microservice-stock
```

## 📝 集成检查清单

### 新服务集成必须项

- [ ] 复制 `nacos_registration_template.py`
- [ ] 安装 `aiohttp` 依赖
- [ ] 设置环境变量
- [ ] 在服务生命周期中调用注册/清理函数
- [ ] 配置 Docker 网络为 `microservice-stock`
- [ ] 添加健康检查端点

### 验证步骤

- [ ] 服务启动后出现在 Nacos 服务列表
- [ ] 每10秒有心跳日志输出
- [ ] 服务实例信息正确（IP、端口、元数据）
- [ ] 服务关闭后从列表中消失

## 🛠️ 常见问题快速解决

### 问题诊断命令

```bash
# 1. 检查 Nacos 状态
curl http://localhost:8848/nacos/

# 2. 检查网络连通性
docker exec your-service ping nacos

# 3. 检查环境变量
docker exec your-service env | grep -E "(NACOS|SERVICE)"

# 4. 查看服务日志
docker logs your-service | tail -50

# 5. 测试手动注册
curl -X POST "http://localhost:8848/nacos/v1/ns/instance" \
  -d "serviceName=test&ip=127.0.0.1&port=9999&groupName=DEFAULT_GROUP"
```

## 📊 监控和维护

### 服务健康监控

```bash
# 监控脚本
#!/bin/bash
while true; do
    echo "$(date): 检查服务状态..."
    curl -s "http://localhost:8848/nacos/v1/ns/instance/list?serviceName=task-scheduler" | jq '.hosts[0].healthy'
    sleep 30
done
```

### 日志监控

```bash
# 实时查看心跳日志
docker logs -f task-scheduler-heartbeat-debug | grep "心跳"

# 查看注册日志
docker logs task-scheduler-heartbeat-debug | grep "注册"
```

## 📚 技术栈信息

### 核心技术

- **服务注册**: Nacos v2.2.3
- **HTTP客户端**: aiohttp
- **容器化**: Docker + Docker Compose
- **网络**: Docker 自定义网络

### 依赖包

```txt
aiohttp>=3.8.0
fastapi>=0.104.0    # 如果使用 FastAPI
uvicorn[standard]>=0.24.0  # 如果使用 FastAPI
```

## 🤝 团队协作

### 代码审查要点

1. **服务命名规范**: 使用小写+连字符
2. **元数据完整**: 包含版本、框架、团队信息
3. **错误处理**: 注册失败不影响服务启动
4. **日志级别**: 适当的信息日志和调试日志
5. **资源清理**: 确保心跳任务正确停止

### 发布流程

1. 在开发环境验证 Nacos 注册
2. 检查心跳机制正常工作
3. 验证服务元数据信息
4. 确认优雅关闭功能
5. 部署到测试环境验证
6. 生产环境发布

## 📞 技术支持

### 联系方式

- **技术负责人**: [团队邮箱]
- **文档维护**: [维护人员]
- **紧急联系**: [联系方式]

### 问题反馈

如果在集成过程中遇到问题：

1. 查看 [实施指南](services/task-scheduler/NACOS_SERVICE_REGISTRATION.md)
2. 参考 [快速部署指南](services/task-scheduler/QUICK_DEPLOYMENT_GUIDE.md)
3. 检查 Task Scheduler 服务的实现
4. 联系技术支持团队

---

**文档维护**: 本索引文档随项目更新，最后更新时间: 2025-11-11
**版本**: 1.0