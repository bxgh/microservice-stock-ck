# Development Workflow

## Local Development Setup

### Prerequisites
```bash
# 检查系统要求
python3 --version  # 需要 Python 3.11+
node --version     # 需要 Node.js 18+
docker --version   # 需要 Docker 24.0+
docker-compose --version  # 需要 Docker Compose 2.20+

# 检查 MySQL 5.7 外部连接
mysql --version    # 确认外部 MySQL 5.7 可访问
```

### Initial Setup
```bash
# 1. 克隆项目
git clone <repository-url> microservice-stock
cd microservice-stock

# 2. 创建 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装前端依赖
cd services/web-ui
npm install
cd ../..

# 4. 复制环境变量模板
cp .env.example .env

# 5. 配置环境变量
# 编辑 .env 文件，配置数据库连接、代理设置等

# 6. 构建所有 Docker 镜像
./scripts/build.sh

# 7. 启动基础服务
docker-compose -f infrastructure/docker-compose.yml up -d redis clickhouse

# 8. 启动开发环境
./scripts/start-dev.sh
```

### Development Commands
```bash
# 启动开发环境
./scripts/start-dev.sh

# 启动所有服务
./scripts/start-dev.sh --all

# 仅启动前端开发服务器
cd services/web-ui
npm run dev

# 仅启动后端开发服务器
cd services/task-scheduler
python src/main.py

# 运行测试
npm run test                    # 前端测试
pytest                          # 后端测试
./scripts/test.sh              # 所有测试
```

## Environment Configuration

### Required Environment Variables

**Frontend (.env.local)**
```bash
# API 配置
REACT_APP_API_BASE_URL=http://localhost:8080/api/v1
REACT_APP_WS_URL=ws://localhost:8080/ws

# 应用配置
REACT_APP_NAME=microservice-stock
REACT_APP_VERSION=1.0.0
```

**Backend (.env)**
```bash
# 数据库配置
MYSQL_HOST=your-mysql-host
MYSQL_PORT=3306
MYSQL_DATABASE=microservice_stock
MYSQL_USER=your-username
MYSQL_PASSWORD=your-password

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379

# ClickHouse 配置
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123

# 代理配置
HTTP_PROXY=http://192.168.151.18:3128
HTTPS_PROXY=http://192.168.151.18:3128

# 时区配置
TIMEZONE=Asia/Shanghai
```
