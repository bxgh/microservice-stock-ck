# 微服务模板使用指南

## 📋 概述

这是一个**最小化的微服务模板**，包含创建新微服务所需的所有核心基础设施。你可以基于此模板快速创建任何新的微服务，无需从零开始配置服务注册、健康检查等基础组件。

## 🎯 模板特性

### ✅ 已包含的核心功能

- **服务注册发现** - Nacos集成，自动服务注册和心跳
- **健康检查** - `/api/v1/health` 端点，支持Kubernetes探针
- **中间件系统** - CORS、日志、认证中间件
- **配置管理** - 环境变量 + 设置文件配置
- **API文档** - 自动生成的Swagger UI
- **生命周期管理** - 优雅启动/关闭
- **容器化部署** - Docker + docker-compose
- **示例代码** - 展示如何创建新的API路由

### 📁 项目结构

```
stock-data/
├── src/
│   ├── api/                    # API层
│   │   ├── __init__.py         # 路由导出
│   │   ├── health_routes.py    # 健康检查路由
│   │   ├── example_routes.py   # 示例业务路由
│   │   └── middleware.py       # 中间件
│   ├── models/                 # 数据模型层
│   │   ├── __init__.py
│   │   └── base_models.py      # 基础模型（ApiResponse等）
│   ├── config/                 # 配置层
│   │   ├── __init__.py
│   │   └── settings.py         # 应用设置
│   ├── registry/               # 服务注册发现
│   │   ├── __init__.py
│   │   └── nacos_registry_simple.py  # Nacos客户端
│   └── main.py                 # 应用入口
├── config/
│   └── taskscheduler.yaml      # 配置文件
├── Dockerfile                  # 容器化配置
├── docker-compose.yml          # 服务编排
├── requirements.txt            # Python依赖
└── README.md                   # 本文档
```

## 🚀 快速开始

### 第一步：复制模板

```bash
# 复制模板到新的服务目录
cp -r services/stock-data services/your-new-service

# 进入新服务目录
cd services/your-new-service
```

### 第二步：修改配置（3个关键文件）

#### 1. 修改服务名称和端口

编辑 `src/config/settings.py`：
```python
class Settings(BaseSettings):
    name: str = "YourNewService"     # ✅ 修改服务名
    version: str = "1.0.0"
    debug: bool = False

    # API配置
    host: str = "0.0.0.0"
    port: int = 8083                   # ✅ 修改端口，避免冲突

    # 其他配置保持不变...
```

#### 2. 修改容器配置

编辑 `docker-compose.yml`：
```yaml
services:
  your-new-service:               # ✅ 修改服务名
    image: your-new-service:latest # ✅ 修改镜像名
    container_name: your-new-service  # ✅ 修改容器名
    restart: unless-stopped
    ports:
      - "8083:8083"                 # ✅ 修改端口
    environment:
      - NACOS_SERVER_URL=http://nacos:8848
      - SERVICE_NAME=your-new-service     # ✅ 修改服务名
      - SERVICE_GROUP=DEFAULT_GROUP
      - SERVICE_PORT=8083                   # ✅ 修改端口
      - LOG_LEVEL=INFO
      - HEARTBEAT_INTERVAL=30
    networks:
      - microservice-stock_microservice-stock
    volumes:
      - your-new-service-logs:/app/logs   # ✅ 修改卷名
    healthcheck:
      test: ["CMD", "curl", "--noproxy", "*", "-f", "http://localhost:8083/api/v1/health"]  # ✅ 修改端口
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  microservice-stock_microservice-stock:
    external: true

volumes:
  your-new-service-logs:           # ✅ 修改卷名
    driver: local
```

#### 3. 修改应用描述

编辑 `src/main.py`，在服务注册部分修改描述：
```python
success = await register_to_nacos(
    service_name=settings.name.lower().replace(" ", "-"),
    service_port=settings.port,
    framework="FastAPI",
    description=f"{settings.name} 微服务 - 基于模板创建"  # ✅ 可以自定义描述
)
```

### 第三步：构建和部署

```bash
# 构建Docker镜像
docker build -t your-new-service:latest .

# 启动服务
docker compose up -d

# 查看服务状态
docker ps
docker logs your-new-service

# 测试服务
curl http://localhost:8083/api/v1/health
```

## 🔧 开发指南

### 添加新的API路由

1. **创建路由文件**
```bash
# 在 src/api/ 目录下创建新路由
touch src/api/your_routes.py
```

2. **编写路由代码**（参考 `example_routes.py`）
```python
"""
你的业务路由
"""

import logging
from fastapi import APIRouter

from models.base_models import ApiResponse

logger = logging.getLogger(__name__)

# 创建路由器
your_router = APIRouter(prefix="/api/v1/your-endpoint", tags=["your-service"])

@your_router.get("/", response_model=None, summary="你的API端点")
async def your_endpoint():
    """你的业务逻辑"""
    try:
        return ApiResponse(
            success=True,
            message="API调用成功",
            data={"message": "这是你的业务数据"}
        )
    except Exception as e:
        logger.error(f"API调用失败: {e}")
        return ApiResponse(
            success=False,
            message=f"API调用失败: {str(e)}"
        )
```

3. **注册路由**
```python
# 在 src/api/__init__.py 中添加
from .your_routes import your_router

# 在 __all__ 中添加
__all__ = ["your_router", "health_router", ...]
```

4. **在主应用中注册路由**
```python
# 在 src/main.py 中导入
from api.your_routes import your_router

# 在 create_app() 函数中添加
def create_app() -> FastAPI:
    app = FastAPI(...)

    # 注册路由
    app.include_router(health_router)
    app.include_router(your_router)  # ✅ 添加你的路由

    return app
```

### 添加数据模型

1. **创建模型文件**
```python
# 在 src/models/ 目录下创建
touch src/models/your_models.py
```

2. **定义模型**（参考 `base_models.py`）
```python
"""
你的数据模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class YourModel(BaseModel):
    """你的数据模型"""
    id: Optional[int] = None
    name: str = Field(..., description="名称")
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### 配置自定义设置

在 `src/config/settings.py` 中添加你的配置项：
```python
class Settings(BaseSettings):
    # 现有配置...

    # 添加你的配置
    your_api_key: str = "default-key"
    your_timeout: int = 30
    your_enabled: bool = True

    # 从环境变量读取
    your_database_url: str = Field(default="sqlite:///app.db", env="DATABASE_URL")
```

## 🔍 验证模板功能

### 基础功能测试

```bash
# 1. 健康检查
curl http://localhost:PORT/api/v1/health
# 期望返回: {"success": true, "data": {"status": "healthy"}}

# 2. 示例API
curl http://localhost:PORT/api/v1/example/
# 期望返回: {"success": true, "data": {"message": "这是一个空白微服务模板"}}

# 3. API文档
open http://localhost:PORT/docs
# 应该看到Swagger UI界面

# 4. 服务注册
curl "http://localhost:8848/nacos/v1/ns/service/list"
# 应该在列表中看到你的服务
```

### 容器健康检查

```bash
# 检查容器状态
docker ps | grep your-new-service
# 应该显示 (healthy) 状态

# 查看启动日志
docker logs your-new-service
# 应该看到服务启动和注册成功的日志
```

## 📝 最佳实践

### 1. 命名规范
- 服务名使用小写字母和连字符：`user-service`
- 镜像名使用服务名：`user-service:latest`
- 容器名使用服务名：`user-service`

### 2. 端口管理
- 每个服务使用不同端口，避免冲突
- 建议：8000-8999 范围用于微服务

### 3. 环境变量
- 敏感信息使用环境变量
- 配置信息通过 `.env` 文件管理
- 在生产环境中使用密钥管理系统

### 4. 日志管理
- 使用结构化日志
- 日志级别：开发环境用 DEBUG，生产环境用 INFO
- 重要操作记录完整日志

### 5. 健康检查
- 实现就绪检查和存活检查
- 检查关键依赖（数据库、外部服务等）
- 返回详细的健康状态信息

## 🚨 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep :PORT
   # 解决：修改配置中的端口号
   ```

2. **服务注册失败**
   ```bash
   # 检查Nacos状态
   docker logs microservice-stock-nacos
   # 确保网络连接正确
   ```

3. **容器启动失败**
   ```bash
   # 查看详细错误日志
   docker logs your-new-service
   # 检查Dockerfile中的命令
   ```

4. **API无法访问**
   ```bash
   # 检查网络配置
   docker network ls
   # 确保容器连接到正确网络
   ```

## 📚 参考资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Nacos 官方文档](https://nacos.io/)
- [Docker 官方文档](https://docs.docker.com/)
- [Pydantic 数据验证](https://pydantic-docs.helpmanual.io/)

---

**🎉 恭喜！现在你拥有了一个可以快速复制和使用的微服务模板！**