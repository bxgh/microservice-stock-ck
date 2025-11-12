# Nacos 服务注册实施指南

## 📋 概述

本文档详细说明了如何在微服务架构中实现 Nacos 服务注册发现，基于 Task Scheduler 微服务的成功实施经验。该方案解决了服务注册、心跳机制、网络配置等关键问题。

## 🎯 核心问题与解决方案

### 1. 服务注册后自动消失问题

**问题描述**：
- 服务注册成功后，很快从 Nacos 服务列表中消失
- 原因：缺少心跳机制，Nacos 认为服务已下线自动剔除

**解决方案**：
- 实现定期心跳发送机制（每10秒一次）
- 在服务启动时自动启动心跳任务
- 在服务关闭时优雅停止心跳任务

### 2. 容器网络IP地址获取问题

**问题描述**：
- 容器内获取的IP地址不正确
- 服务注册使用了错误的网络接口

**解决方案**：
- 优化IP地址获取逻辑，优先获取容器内网IP
- 支持多种IP地址获取策略
- 回退机制确保始终能获取有效IP

### 3. 服务注册重试机制

**问题描述**：
- Nacos服务可能在服务启动时未就绪
- 网络临时波动导致注册失败

**解决方案**：
- 实现3次重试机制，每次间隔5秒
- 即使注册失败也继续运行服务
- 详细的错误日志记录

## 🔧 技术实现方案

### 1. 核心架构

```python
# 主要组件
- SimpleNacosRegistry: Nacos注册类
- heartbeat_task_func(): 心跳任务函数
- register_to_nacos(): 服务注册函数
- get_local_ip(): IP地址获取函数
```

### 2. 服务注册流程

```python
async def register_to_nacos():
    """
    1. 获取容器内网IP地址
    2. 构建服务配置信息
    3. 调用Nacos注册API
    4. 启动心跳任务
    5. 实现重试机制
    """
```

### 3. 心跳机制实现

```python
async def heartbeat_task_func():
    """
    1. 每10秒发送一次心跳
    2. 异步执行，不阻塞主服务
    3. 异常处理和日志记录
    4. 支持优雅关闭
    """
```

### 4. 完整配置示例

```python
service_config = {
    "serviceName": "your-service-name",
    "ip": local_ip,                    # 自动获取容器IP
    "port": service_port,              # 服务端口
    "groupName": "DEFAULT_GROUP",      # 服务组名
    "clusterName": "DEFAULT",          # 集群名称
    "namespaceId": "",                 # 命名空间
    "weight": 1.0,                     # 权重
    "enabled": True,                   # 是否启用
    "healthy": True,                   # 是否健康
    "ephemeral": True,                 # 是否临时实例
    "metadata": {                      # 元数据
        "version": "1.0.0",
        "framework": "FastAPI",
        "environment": "development",
        "description": "服务描述"
    }
}
```

## 📝 其他服务实施步骤

### Step 1: 复制核心代码

```python
# 1. 复制 SimpleNacosRegistry 类
class SimpleNacosRegistry:
    def __init__(self, nacos_url: str):
        self.nacos_url = nacos_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def register_service(self, service_config: dict) -> bool:
        # 注册服务实现
        pass

    async def send_heartbeat(self, service_config: dict) -> bool:
        # 心跳发送实现
        pass

# 2. 复制全局变量
nacos_registry = None
heartbeat_task = None
service_config = None
```

### Step 2: 修改服务配置

```python
# 根据你的服务修改配置
async def register_to_nacos():
    global nacos_registry, service_config

    for attempt in range(max_retries):
        try:
            async with nacos_registry:
                local_ip = get_local_ip()
                port = int(os.getenv("SERVICE_PORT", "YOUR_PORT"))

                service_config = {
                    "serviceName": "your-service-name",  # 修改服务名
                    "ip": local_ip,
                    "port": port,
                    "groupName": "DEFAULT_GROUP",
                    "clusterName": "DEFAULT",
                    "namespaceId": "",
                    "weight": 1.0,
                    "enabled": True,
                    "healthy": True,
                    "ephemeral": True,
                    "metadata": {
                        "version": "1.0.0",
                        "framework": "YourFramework",   # 修改框架名
                        "environment": os.getenv("ENVIRONMENT", "development"),
                        "description": "你的服务描述"
                    }
                }

                # 注册和启动心跳...
```

### Step 3: 集成到应用生命周期

```python
# 在应用启动时调用
async def startup():
    global nacos_registry

    nacos_url = os.getenv("NACOS_SERVER_URL", "http://nacos:8848")
    nacos_registry = SimpleNacosRegistry(nacos_url)

    await register_to_nacos()

# 在应用关闭时清理
async def shutdown():
    global heartbeat_task

    if heartbeat_task:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
```

## 🐳 Docker 容器配置

### 1. 环境变量配置

```yaml
# docker-compose.yml
environment:
  - NACOS_SERVER_URL=http://nacos:8848
  - SERVICE_NAME=your-service-name
  - SERVICE_PORT=YOUR_PORT
  - SERVICE_GROUP=DEFAULT_GROUP
  - LOG_LEVEL=INFO
  - HEARTBEAT_INTERVAL=10
```

### 2. 网络配置

```yaml
# 确保使用相同的网络
networks:
  - microservice-stock

# 或指定外部网络
networks:
  microservice-stock:
    external: true
```

### 3. 健康检查

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:YOUR_PORT/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## 🔍 验证与调试

### 1. 服务注册验证

```bash
# 检查服务列表
curl "http://localhost:8848/nacos/v1/ns/service/list"

# 检查具体服务实例
curl "http://localhost:8848/nacos/v1/ns/instance/list?serviceName=your-service-name"

# 手动测试心跳
curl -X PUT "http://localhost:8848/nacos/v1/ns/instance/beat" \
  -d "serviceName=your-service-name&ip=SERVICE_IP&port=SERVICE_PORT&groupName=DEFAULT_GROUP"
```

### 2. 日志监控

```python
# 关键日志信息
logger.info("✅ 服务注册成功: service_name")
logger.info("💓 心跳任务已启动")
logger.info("💓 心跳发送成功: service_name")
logger.error("❌ 服务注册异常: error_details")
```

### 3. 常见问题排查

| 问题现象 | 可能原因 | 解决方案 |
|---------|----------|----------|
| 服务不在列表中 | 注册失败 | 检查网络连接、Nacos状态 |
| 服务健康状态false | 心跳未发送 | 检查心跳任务是否启动 |
| 服务自动消失 | 心跳停止 | 检查心跳日志，确认定期发送 |
| IP地址不正确 | 网络配置 | 检查容器网络配置 |

## 📋 部署检查清单

### 部署前检查

- [ ] Nacos 服务正常运行
- [ ] Docker 网络配置正确
- [ ] 环境变量设置完整
- [ ] 端口映射配置正确

### 部署后验证

- [ ] 容器启动成功
- [ ] 服务健康检查通过
- [ ] 服务出现在 Nacos 列表中
- [ ] 心跳日志正常输出
- [ ] 服务健康状态为 true（可选）

## 🚀 最佳实践

### 1. 服务命名规范

```python
# 推荐的命名规范
{
    "serviceName": "service-name",          # 小写+连字符
    "groupName": "DEFAULT_GROUP",           # 统一使用默认组
    "clusterName": "DEFAULT",               # 开发环境使用默认
    "namespaceId": ""                       # 使用默认命名空间
}
```

### 2. 元数据规范

```python
metadata = {
    "version": "1.0.0",                    # 语义化版本号
    "framework": "FrameworkName",          # 框架名称
    "environment": "development|staging|production",  # 环境标识
    "description": "服务功能描述",          # 简短描述
    "team": "团队名称",                     # 负责团队
    "repository": "代码仓库地址"            # 代码仓库（可选）
}
```

### 3. 心跳配置

```python
heartbeat_config = {
    "heartbeat_interval": 10,              # 心跳间隔（秒）
    "heartbeat_timeout": 15,               # 心跳超时（秒）
    "delete_timeout": 30,                  # 删除超时（秒）
    "max_retries": 3,                      # 最大重试次数
    "retry_delay": 5                       # 重试延迟（秒）
}
```

## 📚 参考资料

- [Nacos 官方文档](https://nacos.io/zh-cn/docs/what-is-nacos.html)
- [Nacos API 参考](https://nacos.io/zh-cn/docs/open-api.html)
- [aiohttp 文档](https://docs.aiohttp.org/)
- [Docker 网络配置](https://docs.docker.com/network/)

## 🤝 技术支持

如果在实施过程中遇到问题，可以：

1. 参考 Task Scheduler 服务的完整实现
2. 检查 Nacos 服务日志
3. 验证 Docker 网络连接
4. 查看应用日志中的详细错误信息

---

**最后更新**: 2025-11-11
**版本**: 1.0
**基于**: Task Scheduler 微服务成功实施经验