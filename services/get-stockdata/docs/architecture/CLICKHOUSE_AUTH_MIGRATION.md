# ClickHouse 认证配置迁移指南

## 问题描述
ClickHouse 从无密码的 `default` 用户迁移到 `admin/admin123` 用户名密码认证。

## 影响范围
以下组件需要更新 ClickHouse 连接配置：
1. ✅ `src/main.py` - ClickHouseWriter 初始化
2. ✅ `docker-compose.dev.yml` - 容器环境变量
3. ⚠️ `src/core/storage/dual_writer.py` - 使用上游 ClickHouseWriter（已支持）
4. ⚠️ 其他测试脚本/工具（需手动检查）

## 已完成的修改

### 1. `src/main.py`
```python
writer = ClickHouseWriter(
    host=os.getenv('CLICKHOUSE_HOST', 'microservice-stock-clickhouse'),
    port=int(os.getenv('CLICKHOUSE_PORT', '9000')),
    database=os.getenv('CLICKHOUSE_DB', 'stock_data'),
    user=os.getenv('CLICKHOUSE_USER', 'default'),      # 新增
    password=os.getenv('CLICKHOUSE_PASSWORD', ''),      # 新增
    batch_size=1000
)
```

### 2. `docker-compose.dev.yml`
添加了环境变量（默认值为 admin/admin123）：
```yaml
environment:
  - CLICKHOUSE_HOST=${CLICKHOUSE_HOST:-microservice-stock-clickhouse}
  - CLICKHOUSE_PORT=${CLICKHOUSE_PORT:-9000}
  - CLICKHOUSE_DB=${CLICKHOUSE_DB:-stock_data}
  - CLICKHOUSE_USER=${CLICKHOUSE_USER:-admin}
  - CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD:-admin123}
```

## 使用方法

### 方法 1: 使用默认值（推荐）
环境变量已在 `docker-compose.dev.yml` 中设置默认值为 `admin/admin123`，无需额外配置。

### 方法 2: 使用 .env 文件
创建 `.env` 文件（参考 `.env.example`）：
```bash
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=admin123
```

### 方法 3: 在宿主机设置环境变量
```bash
export CLICKHOUSE_USER=admin
export CLICKHOUSE_PASSWORD=admin123
docker compose -f docker-compose.dev.yml up -d
```

## 验证配置
```bash
# 重启容器
docker compose -f docker-compose.dev.yml up -d get-stockdata

# 检查日志，应看到连接成功
docker logs get-stockdata-api-dev | grep "ClickHouse 客户端已连接"
```

## 需要手动检查的文件/脚本
以下文件可能直接使用 ClickHouse 连接，需手动更新：
- [ ] `scripts/run_init_clickhouse.py` (已使用 `os.getenv('CLICKHOUSE_PASSWORD', '')`)
- [ ] `tests/` 中的测试脚本
- [ ] 其他独立工具脚本

## 回滚方案
如需恢复为无密码：
```bash
# 修改 docker-compose.dev.yml 默认值
- CLICKHOUSE_USER=${CLICKHOUSE_USER:-default}
- CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD:-}
```
