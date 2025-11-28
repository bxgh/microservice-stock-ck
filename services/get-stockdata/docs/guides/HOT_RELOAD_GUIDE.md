# 开发环境热加载配置指南

## 🔥 热加载支持

本项目现在支持**开发环境热加载**，代码修改后会自动重启服务，无需手动重启容器！

---

## 📁 文件说明

| 文件 | 用途 | 热加载 | 源码挂载 |
|------|------|--------|----------|
| `docker-compose.yml` | **生产环境** | ❌ 否 | ❌ 否 |
| `docker-compose.dev.yml` | **开发环境** | ✅ 是 | ✅ 是 |

> **注意**: `tests/` 目录已挂载到容器中，修改测试代码**不会**触发服务重启，但可以在容器内直接运行最新测试。

---

## 🚀 使用方法

### 开发环境（推荐）

```bash
# 启动开发环境（支持热加载）
docker compose -f docker-compose.dev.yml up --build

# 或者后台运行
docker compose -f docker-compose.dev.yml up -d

# 查看实时日志
docker compose -f docker-compose.dev.yml logs -f
```

**特性**:
- ✅ **自动热加载**: 修改 `src/` 目录下的任何 Python 文件都会自动重启服务
- ✅ **即时生效**: 无需重启容器，修改代码后 1-2 秒即可生效
- ✅ **详细日志**: DEBUG 级别日志，方便调试
- ✅ **配置热加载**: `config/` 目录也支持热加载

### 生产环境

```bash
# 启动生产环境（无热加载，性能更高）
docker compose up --build -d

# 查看日志
docker compose logs -f
```

---

## 🔍 热加载工作原理

开发环境使用 `uvicorn --reload --reload-dir /app/src` 参数监控文件变化。

当 `src/` 目录下的文件修改时：
1. Uvicorn 检测到文件变化
2. 自动杀死当前进程
3. 重新加载 Python 模块
4. 启动新进程（约 1-2 秒）

---

## 💡 快速示例

```bash
# 1. 启动开发环境
docker compose -f docker-compose.dev.yml up

# 2. 修改代码（例如 src/services/fenbi_engine.py）
nano src/services/fenbi_engine.py

# 3. 保存后自动重启（约 1-2 秒）
# 日志会显示: "Detected file change in 'src/services/fenbi_engine.py'"

# 4. 测试新代码
curl http://localhost:8086/api/v1/health
```

---

## ⚠️ 注意事项

### ✅ 可以热加载的修改
- Python 源码文件 (`.py`)
- 配置文件
- 业务逻辑、API 路由

### ❌ 需要重新构建的修改
- `requirements.txt` 依赖变化
- `Dockerfile` 修改
- 系统级依赖

重新构建命令：
```bash
docker compose -f docker-compose.dev.yml up --build
```

---

## 📊 性能对比

| 对比项 | 生产环境 | 开发环境(热加载) |
|--------|---------|-----------------|
| 代码修改生效 | 需重启容器(~30秒) | **自动重启(~1-2秒)** ✅ |
| 日志详细度 | INFO | DEBUG |
| 适用场景 | 生产部署 | 本地开发/调试 |

---

**🎉 享受丝滑的开发体验！修改代码，保存，1-2秒后自动生效！**
