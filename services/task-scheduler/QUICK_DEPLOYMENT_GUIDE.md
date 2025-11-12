# Nacos 服务注册快速部署指南

## 🚀 5分钟快速集成

### 第一步：复制核心文件

```bash
# 1. 复制 Nacos 注册模板到你的服务目录
cp /path/to/nacos_registration_template.py your_service/nacos_registry.py

# 2. 安装依赖
pip install aiohttp
```

### 第二步：集成到你的服务

```python
# 在你的服务主文件中添加以下代码

import asyncio
from nacos_registry import initialize_nacos, register_to_nacos, cleanup_nacos

# 在服务启动时调用
async def startup():
    """服务启动初始化"""
    # 1. 初始化 Nacos
    await initialize_nacos()

    # 2. 注册服务
    success = await register_to_nacos(
        service_name="your-service-name",      # 修改为你的服务名
        service_port=8080,                     # 修改为你的端口
        framework="YourFramework",             # 修改为你的框架
        description="你的服务描述",             # 修改为服务描述
        additional_metadata={                  # 可选的额外元数据
            "team": "your-team",
            "version": "1.0.0"
        }
    )

    if success:
        print("✅ 服务注册成功")
    else:
        print("❌ 服务注册失败")

# 在服务关闭时调用
async def shutdown():
    """服务关闭清理"""
    await cleanup_nacos()

# 在你的应用生命周期中调用
# FastAPI 示例：
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup()
    yield
    await shutdown()

app = FastAPI(lifespan=lifespan)

# 或者其他框架的启动/关闭钩子
```

### 第三步：配置环境变量

```bash
# 设置环境变量
export NACOS_SERVER_URL=http://nacos:8848
export SERVICE_NAME=your-service-name
export SERVICE_PORT=8080
export ENVIRONMENT=development
```

### 第四步：Docker 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  your-service:
    build: .
    container_name: your-service
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - NACOS_SERVER_URL=http://nacos:8848
      - SERVICE_NAME=your-service-name
      - SERVICE_PORT=8080
      - ENVIRONMENT=development
    networks:
      - microservice-stock
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  microservice-stock:
    external: true
```

### 第五步：验证部署

```bash
# 1. 检查服务是否在 Nacos 中注册
curl "http://localhost:8848/nacos/v1/ns/service/list"

# 2. 检查服务实例详情
curl "http://localhost:8848/nacos/v1/ns/instance/list?serviceName=your-service-name"

# 3. 检查服务健康状态
curl "http://localhost:8080/health"

# 4. 查看服务日志
docker logs your-service | grep -E "(服务注册|心跳|Nacos)"
```

## 📋 部署检查清单

### ✅ 必要条件

- [ ] Nacos 服务正在运行（http://localhost:8848/nacos）
- [ ] Docker 网络已配置（microservice-stock）
- [ ] 服务端口未被占用
- [ ] aiohttp 依赖已安装

### ✅ 配置检查

- [ ] 服务名称符合规范（小写+连字符）
- [ ] 端口配置正确
- [ ] 环境变量设置完整
- [ ] 元数据信息完整

### ✅ 运行验证

- [ ] 容器启动成功
- [ ] 健康检查通过
- [ ] 服务出现在 Nacos 列表
- [ ] 心跳日志正常输出

## 🔧 常见问题解决

### 问题1：服务注册失败

**症状**：日志显示 "服务注册失败"

**解决方案**：
```bash
# 检查 Nacos 连接
curl http://nacos:8848/nacos/v1/ns/service/list

# 检查网络连通性
docker exec your-service ping nacos

# 检查环境变量
docker exec your-service env | grep NACOS
```

### 问题2：服务自动消失

**症状**：服务注册成功后很快从列表消失

**解决方案**：
```bash
# 检查心跳日志
docker logs your-service | grep "心跳"

# 确保心跳任务已启动
docker logs your-service | grep "心跳任务已启动"
```

### 问题3：IP地址错误

**症状**：服务注册使用了错误的IP地址

**解决方案**：
```bash
# 检查容器IP
docker inspect your-service | grep IPAddress

# 手动测试IP获取
docker exec your-service python -c "
import socket
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)
print(f'Hostname: {hostname}, IP: {local_ip}')
"
```

## 📝 最佳实践

### 1. 服务命名规范

```python
# ✅ 推荐
service_name = "user-service"
service_name = "order-service"
service_name = "payment-gateway"

# ❌ 不推荐
service_name = "UserService"
service_name = "userservice"
service_name = "user_service"
```

### 2. 元数据规范

```python
metadata = {
    "version": "1.0.0",                    # 语义化版本
    "framework": "FastAPI",                # 框架名称
    "environment": "production",           # 环境
    "description": "用户管理服务",           # 中文描述
    "team": "backend-team",               # 负责团队
    "repository": "https://github.com/...", # 代码仓库
    "contact": "team@company.com"          # 联系方式
}
```

### 3. 错误处理

```python
try:
    success = await register_to_nacos(...)
    if not success:
        # 注册失败，但服务继续运行
        logger.warning("服务注册失败，但服务继续运行")
except Exception as e:
    # 异常处理
    logger.error(f"服务注册异常: {e}")
    # 决定是否继续运行服务
```

## 🧪 测试命令

```bash
# 完整的测试脚本
#!/bin/bash

echo "🧪 开始 Nacos 服务注册测试..."

# 1. 检查 Nacos 状态
echo "1. 检查 Nacos 状态..."
curl -s http://localhost:8848/nacos/ > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Nacos 服务正常"
else
    echo "❌ Nacos 服务异常"
    exit 1
fi

# 2. 检查服务注册
echo "2. 检查服务注册..."
services=$(curl -s "http://localhost:8848/nacos/v1/ns/service/list" | jq -r '.doms[]' 2>/dev/null)
if echo "$services" | grep -q "your-service-name"; then
    echo "✅ 服务已注册到 Nacos"
else
    echo "❌ 服务未注册到 Nacos"
fi

# 3. 检查服务实例
echo "3. 检查服务实例..."
instances=$(curl -s "http://localhost:8848/nacos/v1/ns/instance/list?serviceName=your-service-name")
if echo "$instances" | jq -e '.hosts | length > 0' > /dev/null 2>&1; then
    echo "✅ 服务实例存在"
    echo "$instances" | jq '.hosts[0] | {ip, port, healthy, enabled}'
else
    echo "❌ 服务实例不存在"
fi

# 4. 检查服务健康
echo "4. 检查服务健康..."
curl -s -f http://localhost:8080/health > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ 服务健康检查通过"
else
    echo "❌ 服务健康检查失败"
fi

echo "🎉 测试完成！"
```

## 📚 相关文档

- [完整实施指南](./NACOS_SERVICE_REGISTRATION.md)
- [Nacos 官方文档](https://nacos.io/zh-cn/docs/)
- [Docker 网络配置](https://docs.docker.com/network/)

---

**快速成功标准**：如果你的服务在 Nacos Web 界面的"服务管理 > 服务列表"中可见，并且每10秒能在日志中看到心跳信息，则表示集成成功！