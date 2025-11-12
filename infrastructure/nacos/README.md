# Nacos 服务注册发现中心

Nacos 是阿里巴巴开源的一个更易于构建云原生应用的动态服务发现、配置管理和服务管理平台。

## 🚀 快速开始

### 方式1：使用启动脚本（推荐）

```bash
# 启动 Nacos
./infrastructure/nacos/start-nacos.sh start

# 检查状态
./infrastructure/nacos/start-nacos.sh status

# 查看日志
./infrastructure/nacos/start-nacos.sh logs

# 停止 Nacos
./infrastructure/nacos/start-nacos.sh stop
```

### 方式2：使用 Docker Compose

```bash
# 仅启动 Nacos
docker compose -f docker-compose.nacos.yml up -d

# 启动完整基础设施
docker compose -f docker-compose.infrastructure.yml up -d
```

## 📋 服务信息

- **访问地址**: http://localhost:8848/nacos
- **默认用户名**: nacos
- **默认密码**: nacos
- **健康检查**: http://localhost:8848/nacos/v1/console/health
- **API接口**: http://localhost:8848/nacos/v1

## 📁 目录结构

```
infrastructure/nacos/
├── config/
│   ├── application.properties     # 主配置文件
│   ├── nacos-logback.xml          # 日志配置
│   ├── cluster.conf               # 集群配置
│   └── application-prod.properties # 生产环境配置
├── mysql-schema.sql               # MySQL 数据库初始化脚本
├── start-nacos.sh                 # 启动脚本
└── README.md                      # 本文档
```

## ⚙️ 配置说明

### application.properties

主要配置项：
- `spring.datasource.platform=embedded` - 使用嵌入式数据库
- `nacos.standalone=true` - 单机模式
- `nacos.core.auth.enabled=false` - 关闭认证（开发环境）
- `JVM_XMS=256m` / `JVM_XMX=256m` - JVM 内存设置

### 集群配置

如果要部署集群：
1. 修改 `cluster.conf` 文件，添加所有节点IP
2. 设置 `spring.datasource.platform=mysql`
3. 初始化 MySQL 数据库（使用 `mysql-schema.sql`）
4. 配置数据库连接信息

## 🔧 集成到微服务

### 1. 环境变量配置

```bash
# .env 文件
REGISTRY_TYPE=nacos
NACOS_URL=http://localhost:8848
NACOS_NAMESPACE=dev
NACOS_GROUP=DEFAULT_GROUP
```

### 2. Python 客户端使用

```python
from nacos import NacosClient

# 创建客户端
client = NacosClient(server_addresses="localhost:8848", namespace="dev")

# 服务注册
client.add_naming_instance(
    service_name="task-scheduler",
    ip="192.168.1.100",
    port=8080,
    cluster_name="DEFAULT",
    weight=1.0,
    metadata={"version": "2.0.0"}
)

# 服务发现
instances = client.list_naming_instance(
    service_name="task-scheduler",
    cluster_name="DEFAULT",
    healthy_only=True
)
```

### 3. 配置管理

```python
# 获取配置
config = client.get_config(
    data_id="application.yml",
    group="DEFAULT_GROUP"
)

# 发布配置
client.publish_config(
    data_id="application.yml",
    group="DEFAULT_GROUP",
    content="key: value"
)
```

## 📊 监控和管理

### 健康检查

```bash
curl http://localhost:8848/nacos/v1/console/health
```

### 服务列表

```bash
curl http://localhost:8848/nacos/v1/ns/service/list
```

### 配置列表

```bash
curl http://localhost:8848/nacos/v1/cs/configs
```

## 🚨 故障排查

### 1. 容器启动失败

```bash
# 查看容器日志
docker logs microservice-stock-nacos

# 检查端口占用
netstat -tunlp | grep 8848
```

### 2. 无法访问控制台

- 检查防火墙设置
- 确认端口映射正确
- 检查容器网络配置

### 3. 服务注册失败

- 检查网络连通性
- 确认 Nacos 服务正常运行
- 检查服务配置格式

### 4. 配置无法加载

- 检查配置格式是否正确
- 确认命名空间和分组名称
- 查看配置历史记录

## 🏗️ 生产环境部署

### 1. 数据库配置

```properties
# 使用 MySQL
spring.datasource.platform=mysql
db.num=1
db.url.0=jdbc:mysql://mysql-host:3306/nacos_config
db.user.0=nacos
db.password.0=nacos
```

### 2. 安全配置

```properties
# 启用认证
nacos.core.auth.enabled=true
nacos.core.auth.default.token.secret.key=your-secret-key
nacos.core.auth.plugin.nacos.token.secret.key=your-secret-key
```

### 3. 集群配置

```properties
# 集群模式
nacos.core.auth.enabled=true
nacos.core.auth.system.type=nacos
```

### 4. 性能优化

```properties
# JVM 优化
JVM_XMS=2g
JVM_XMX=2g

# 连接池优化
server.tomcat.max-threads=200
server.tomcat.min-spare-threads=10
```

## 📚 更多资源

- [Nacos 官方文档](https://nacos.io/zh-cn/docs/what-is-nacos.html)
- [Nacos GitHub](https://github.com/alibaba/nacos)
- [Nacos 快速开始](https://nacos.io/zh-cn/docs/quick-start.html)
- [Nacos API 文档](https://nacos.io/zh-cn/docs/open-api.html)

## 🤝 贡献

如果您发现任何问题或有改进建议，请提交 Issue 或 Pull Request。