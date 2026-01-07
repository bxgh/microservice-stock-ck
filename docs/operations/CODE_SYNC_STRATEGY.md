# 代码同步与配置管理策略

## 1. 文件分类

### 1.1 需要 Git 同步的文件 (全服务器一致)

```
microservice-stock/
├── services/
│   ├── gsd-worker/
│   │   ├── Dockerfile              ✅ Git
│   │   ├── requirements.txt        ✅ Git
│   │   └── src/                    ✅ Git (全部代码)
│   └── mootdx-api/
│       ├── Dockerfile              ✅ Git
│       ├── requirements.txt        ✅ Git
│       └── src/                    ✅ Git (全部代码)
├── config/
│   └── hs300_stocks.yaml           ✅ Git (股票池配置)
├── docker-compose.yml              ✅ Git (模板)
└── .gitlab-ci.yml                  ✅ Git (CI/CD 配置)
```

### 1.2 不入 Git 的本地文件 (各服务器独立)

```
/opt/microservice-stock/
├── .env                            ❌ 本地 (SHARD_INDEX 不同)
├── .env.local                      ❌ 本地 (敏感信息)
└── logs/                           ❌ 本地 (日志目录)
```

---

## 2. 环境变量策略

### 2.1 各服务器 `.env` 文件

**Server 41 (`/opt/microservice-stock/.env`):**
```bash
# 分片配置 (每台服务器不同)
SHARD_INDEX=0
SHARD_TOTAL=3

# ClickHouse 配置 (写入本地)
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000

# mootdx-api 配置
MOOTDX_API_URL=http://localhost:8003
TDX_POOL_SIZE=3
```

**Server 58 (`/opt/microservice-stock/.env`):**
```bash
SHARD_INDEX=1
SHARD_TOTAL=3
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
MOOTDX_API_URL=http://localhost:8003
TDX_POOL_SIZE=3
```

**Server 111 (`/opt/microservice-stock/.env`):**
```bash
SHARD_INDEX=2
SHARD_TOTAL=3
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
MOOTDX_API_URL=http://localhost:8003
TDX_POOL_SIZE=3
```

### 2.2 `.env.example` 模板 (入 Git)

```bash
# .env.example - 复制为 .env 并修改
SHARD_INDEX=0           # 0=Server41, 1=Server58, 2=Server111
SHARD_TOTAL=3
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
MOOTDX_API_URL=http://localhost:8003
TDX_POOL_SIZE=3
```

---

## 3. Docker Compose 配置

### 3.1 通用模板 (入 Git)

**`docker-compose.yml`:**
```yaml
version: "3.8"

services:
  mootdx-api:
    image: ${REGISTRY:-local}/mootdx-api:${TAG:-latest}
    container_name: mootdx-api
    restart: always
    ports:
      - "8003:8003"
    environment:
      - TDX_POOL_SIZE=${TDX_POOL_SIZE:-3}
    networks:
      - stock-net

  gsd-worker:
    image: ${REGISTRY:-local}/gsd-worker:${TAG:-latest}
    container_name: gsd-worker
    environment:
      - MOOTDX_API_URL=${MOOTDX_API_URL:-http://mootdx-api:8003}
      - CLICKHOUSE_HOST=${CLICKHOUSE_HOST:-localhost}
      - CLICKHOUSE_PORT=${CLICKHOUSE_PORT:-9000}
      - SHARD_INDEX=${SHARD_INDEX}      # 从 .env 读取
      - SHARD_TOTAL=${SHARD_TOTAL:-3}
    volumes:
      - ./config:/app/config:ro
    network_mode: host
    profiles:
      - worker  # 手动触发时使用

networks:
  stock-net:
    driver: bridge
```

---

## 4. 部署流程

### 4.1 首次部署 (每台服务器执行一次)

```bash
# 1. 克隆代码
cd /opt
git clone http://192.168.151.58/your-group/microservice-stock.git
cd microservice-stock

# 2. 创建本地 .env (根据服务器修改 SHARD_INDEX)
cp .env.example .env
vi .env  # 修改 SHARD_INDEX

# 3. 启动服务
docker-compose up -d mootdx-api
```

### 4.2 日常更新 (代码变更后)

```bash
# 方式 A: 手动更新
cd /opt/microservice-stock
git pull origin main
docker-compose build
docker-compose up -d

# 方式 B: GitLab CI/CD 自动部署 (推荐)
# Push 代码后自动触发 → 构建镜像 → 部署到各节点
```

### 4.3 执行采集任务

```bash
# 手动触发 (使用 .env 中的 SHARD_INDEX)
docker-compose run --rm gsd-worker \
  python -m jobs.sync_tick --scope all --date 20260107
```

---

## 5. 配置文件同步策略

| 文件类型 | 同步方式 | 说明 |
|----------|----------|------|
| 业务代码 | Git + CI/CD | 全服务器一致 |
| Dockerfile | Git | 全服务器一致 |
| docker-compose.yml | Git | 模板，通过 .env 差异化 |
| .env | **不入 Git** | 各服务器独立配置 |
| config/ 目录 | Git | 股票池等业务配置 |
| ClickHouse 配置 | 本地独立 | 已由集群管理 |

---

## 6. .gitignore 配置

```gitignore
# 环境配置 (不入 Git)
.env
.env.local
.env.*.local

# 日志
logs/
*.log

# Python
__pycache__/
*.pyc
.venv/

# Docker
docker-compose.override.yml
```

---

## 7. 快速参考

### 代码更新检查清单

- [ ] 代码是否已 push 到 GitLab
- [ ] 各服务器 .env 是否正确配置
- [ ] docker-compose.yml 是否拉取最新
- [ ] 镜像是否重新构建
- [ ] 服务是否重启

### 各服务器 SHARD_INDEX 速查

| 服务器 | IP | SHARD_INDEX |
|--------|-----|-------------|
| Server 41 | 192.168.151.41 | 0 |
| Server 58 | 192.168.151.58 | 1 |
| Server 111 | 192.168.151.111 | 2 |
