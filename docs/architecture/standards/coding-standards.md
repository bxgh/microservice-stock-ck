# Coding Standards

## Critical Fullstack Rules

- **Type Sharing:** Always define types in packages/shared and import from there
- **API Calls:** Never make direct HTTP calls - use the service layer
- **Environment Variables:** Access only through config objects, never process.env directly
- **Error Handling:** All API routes must use the standard error handler
- **State Updates:** Never mutate state directly - use proper state management patterns
- **Database Transactions:** Always use database transactions for multi-table operations
- **Logging:** Use structured JSON logging with consistent format across all services
- **Docker Images:** Always use specific version tags, never 'latest' in production
- **Data Source:** **NEVER** call third-party data libraries (e.g., Baostock, AkShare) directly in business logic. All data must be fetched through the `mootdx-source` unified data source layer via gRPC or HTTP.

## Naming Conventions

| Element | Frontend | Backend | Example |
|---------|----------|---------|---------|
| Components | PascalCase | - | `UserProfile.vue` |
| Composables | camelCase with 'use' | - | `useAuth.ts` |
| API Routes | - | kebab-case | `/api/user-profile` |
| Database Tables | - | snake_case | `user_profiles` |
| Environment Variables | UPPER_SNAKE_CASE | UPPER_SNAKE_CASE | `DATABASE_URL` |
| Functions | camelCase | snake_case | `getUserData()` / `get_user_data()` |

## Data Source Standards

### Unified Access Pattern
1. **Entry Point**: All services requiring market or financial data must communicate with `mootdx-source`.
2. **Protocol**: Prefer **gRPC** for internal microservice communication to ensure low latency and strong typing.
3. **Decoupling**: Business services should not know the details of data provider (Mootdx, Baostock, AkShare).
4. **Resilience**: The data source layer is responsible for retries, fallbacks, and rate limiting.

### Prohibited Actions
- `import akshare`, `import baostock`, or `import mootdx` in any service other than `mootdx-source`.
- Direct database access to other microservices' private databases.
- Hardcoded cloud API keys or endpoints in business services.

## Base Container Configuration Standards

### Python Base Image
Use specific Python versions for consistency and security:

```dockerfile
FROM python:3.12-slim
```

**标准规则**：
- 使用 `3.12-slim` 作为当前项目标准版本
- 禁止使用 `latest` 标签
- 优先使用 `-slim` 变体以减小镜像体积

### Working Directory
Always set a consistent working directory:

```dockerfile
WORKDIR /app
```

### Timezone Configuration
Set timezone to China Standard Time for all services:

```dockerfile
# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
```

### Python Environment Variables
Configure Python runtime behavior:

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src
```

**变量说明**：
- `PYTHONDONTWRITEBYTECODE=1`: 禁止生成 `.pyc` 字节码文件
- `PYTHONUNBUFFERED=1`: 强制 stdout/stderr 无缓冲，实时输出日志
- `PYTHONPATH`: 设置 Python 模块搜索路径

### Non-Root User
Create and use a non-root user for security:

```dockerfile
# 创建非root用户和目录
RUN useradd --create-home --shell /bin/bash app && \
    mkdir -p /app/logs /app/data && \
    chown -R app:app /app

# 切换到非root用户
USER app
```

**最佳实践**：
- 用户名统一为 `app`
- 创建必要的数据和日志目录
- 在复制代码后、启动前切换用户
- 使用 `chown` 确保文件权限正确

### Health Check Configuration
Configure appropriate health checks for each service type:

**REST API 服务** (FastAPI, Flask):
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8083/api/v1/health')"
```

**gRPC 服务**:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:50051/ || exit 1
```

**参数说明**：
- `--interval=30s`: 检查间隔
- `--timeout=10s`: 单次检查超时时间
- `--start-period=30s`: 容器启动后的宽限期
- `--retries=3`: 失败重试次数

```

## Container Port Allocation

### Infrastructure Services (基础设施)

| Service | Port(s) | Protocol | Purpose | Access |
|---------|---------|----------|---------|--------|
| **Nacos** | 8848 | HTTP | Console/API | External |
| | 9848 | gRPC | Client communication | Internal |
| | 7848 | TCP | Cluster communication | Internal |
| **Redis** | 6379 | TCP | Cache service | Internal |
| **ClickHouse** | 8123 | HTTP | HTTP interface | Internal |
| | 9000 | TCP | Native protocol | Internal |
| | 9004 | TCP | MySQL protocol | Internal |
| | 9009 | TCP | Replication | Internal |
| **RabbitMQ** | 5672 | AMQP | Message queue | Internal |
| | 15672 | HTTP | Management UI | External |
| **Prometheus** | 9091 | HTTP | Metrics collection | External |
| **Grafana** | 3000 | HTTP | Monitoring dashboard | External |
| **Nginx** | 8080 | HTTP | API Gateway | External |
| | 8443 | HTTPS | API Gateway (SSL) | External |

### Application Services (应用服务)

| Service | Port | Protocol | Purpose | Network Mode |
|---------|------|----------|---------|--------------|
| **get-stockdata** | 8083 | HTTP | REST API | Bridge |
| **mootdx-api** | 8003 | HTTP | TDX Data API | Host |
| **mootdx-source** | 50051 | gRPC | Unified data source | Host |
| **quant-strategy** | 8084 | HTTP | Strategy engine | Bridge |
| **task-scheduler** | 8085 | HTTP | Task scheduling | Bridge |

### Port Range Allocation (端口范围分配)

| Range | Purpose | Examples |
|-------|---------|----------|
| `8000-8099` | REST API services | 8003(mootdx-api), 8083(get-stockdata), 8084(quant-strategy) |
| `50050-50099` | gRPC services | 50051(mootdx-source) |
| `6000-6999` | Databases & Cache | 6379(Redis) |
| `8100-8199` | HTTP interfaces | 8123(ClickHouse), 8848(Nacos) |
| `9000-9099` | Monitoring & Native protocols | 9000(ClickHouse), 9091(Prometheus) |
| `3000-3999` | UI & Dashboards | 3000(Grafana) |
| `5000-5999` | Message Queues | 5672(RabbitMQ) |
| `15000-15999` | Management interfaces | 15672(RabbitMQ) |

### Port Configuration Best Practices

1. **Avoid port conflicts**: Check `docker-compose` files before assigning new ports
2. **Document in Dockerfile**: Always add comments for exposed ports
3. **Consistent mapping**: Use same internal/external port when possible (except conflicts)
4. **Security consideration**: Only expose necessary ports externally
5. **Network mode awareness**:
   - `host` mode: Service uses host network directly, no port mapping needed
   - `bridge` mode: Requires explicit port mapping in docker-compose

### Example Port Configuration

```dockerfile
# Single port
EXPOSE 8083

# Multiple ports with comments
EXPOSE 8083  # REST API
EXPOSE 9090  # Metrics endpoint
EXPOSE 50051 # gRPC service
```

In `docker-compose.yml`:
```yaml
services:
  myservice:
    ports:
      - "8083:8083"  # REST API
      - "9090:9090"  # Metrics
```

### Directory Structure
Create standard directories for logs and data:

```dockerfile
RUN mkdir -p /app/logs /app/data /app/config && \
    chown -R app:app /app
```

**标准目录**：
- `/app`: 应用根目录
- `/app/src`: 源代码
- `/app/config`: 配置文件
- `/app/logs`: 日志文件
- `/app/data`: 数据文件（缓存、临时文件等）

### Entrypoint and CMD
Use entrypoint for initialization scripts and CMD for the main process:

```dockerfile
# 复制并设置权限
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 设置入口点和启动命令
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "src/main.py"]
```

**用途区分**：
- `ENTRYPOINT`: 初始化脚本（环境检查、等待依赖服务等）
- `CMD`: 主进程启动命令（可被 docker run 覆盖）

## Dockerfile Proxy Configuration

### Build Arguments for Proxy
All Dockerfiles should support optional proxy configuration via build arguments:

```dockerfile
# 构建参数
ARG ENABLE_PROXY=true
ARG PROXY_URL=http://192.168.151.18:3128
```

### APT Proxy Configuration
Configure apt to use proxy for package downloads and switch to domestic mirrors:

```dockerfile
# 配置apt代理和源
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        echo 'Acquire::http::Proxy "'$PROXY_URL'";' > /etc/apt/apt.conf.d/00proxy && \
        echo 'Acquire::https::Proxy "'$PROXY_URL'";' >> /etc/apt/apt.conf.d/00proxy && \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    else \
        rm -f /etc/apt/apt.conf.d/00proxy; \
    fi
```

### Pip Mirror Configuration
Use domestic pip mirrors to avoid HTTPS proxy tunnel issues:

```dockerfile
# 配置pip国内镜像源
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = http://mirrors.aliyun.com/pypi/simple/' >> ~/.pip/pip.conf && \
    echo 'trusted-host = mirrors.aliyun.com' >> ~/.pip/pip.conf && \
    echo 'timeout = 120' >> ~/.pip/pip.conf
```

**选择镜像源时的建议**：
- **Aliyun**: `http://mirrors.aliyun.com/pypi/simple/` (推荐用于 HTTP 代理环境)
- **Tencent Cloud**: `https://mirrors.cloud.tencent.com/pypi/simple/` (推荐用于 HTTPS 环境)
- **清华**: `https://pypi.tuna.tsinghua.edu.cn/simple/`

### Pip Install with Proxy
For operations that need to access external PyPI mirrors, conditionally apply proxy:

```dockerfile
# 升级pip (通过代理)
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install --no-cache-dir --upgrade pip; \
    else \
        pip install --no-cache-dir --upgrade pip; \
    fi

# 安装依赖 (通过代理)
COPY requirements.txt .
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi
```

### Build Command
When building images, pass proxy arguments via `--build-arg`:

```bash
docker build \
  --build-arg ENABLE_PROXY=true \
  --build-arg PROXY_URL=http://192.168.151.18:3128 \
  -t myservice:latest .
```

To disable proxy for builds on servers with direct internet access:

```bash
docker build --build-arg ENABLE_PROXY=false -t myservice:latest .
```

### Best Practices
1. **HTTP over HTTPS for mirrors**: Use HTTP for domestic mirrors to avoid HTTPS proxy CONNECT tunnel overhead.
2. **Conditional proxy**: Always make proxy optional via `ENABLE_PROXY` build argument.
3. **Cleanup**: Remove proxy config files when `ENABLE_PROXY=false` to avoid stale configurations.
4. **Mirror selection**: Choose mirrors geographically close to build servers for optimal speed.
5. **Timeout settings**: Set reasonable pip timeout (120s) to handle slow connections.
