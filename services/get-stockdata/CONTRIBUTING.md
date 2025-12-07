# 🚀 开发者贡献指南

欢迎贡献代码！本文档将帮助你快速上手开发。

---

## ⚡ 快速开始（30秒）

```bash
# 1. 进入项目目录
cd services/get-stockdata

# 2. 启动开发环境（推荐）
./start.sh

# 或者使用 Makefile
make dev

# 或者直接使用 docker compose
docker compose -f docker-compose.dev.yml up
```

**就这么简单！** 修改代码后会自动重启（1-2秒），无需手动操作！

---

## 🔥 开发环境说明

### 为什么要使用开发环境？

| 对比项 | 开发环境 | 生产环境 |
|-------|---------|----------|
| 热加载 | ✅ 是（1-2秒） | ❌ 否 |
| 修改生效 | **自动** | 需重启容器(~30秒) |
| 日志级别 | DEBUG | INFO |
| 开发效率 | **极高** | 低 |
| 适用场景 | 本地开发/调试 | 生产部署 |

### 开发环境包含什么？

- ✅ **自动热加载**: 监控 `src/` 目录，代码修改后自动重启
- ✅ **源码挂载**: 本地代码直接映射到容器，无需重新构建
- ✅ **详细日志**: DEBUG 级别日志，方便排查问题
- ✅ **快速反馈**: 修改→保存→等待1-2秒→生效

---

## 📖 详细使用指南

### 方式 1: 交互式启动脚本（推荐新手）

```bash
./start.sh
```

会看到友好的菜单：
```
════════════════════════════════════════════════════════════
  Get Stock Data 微服务启动向导
════════════════════════════════════════════════════════════

请选择启动模式:

  1) 🔥 开发环境（推荐）- 支持热加载
  2) 🚀 生产环境 - 高性能
  3) 📊 查看服务状态
  4) 🛑 停止所有服务
  5) 📋 查看日志
  6) ❓ 帮助文档
  0) 退出
```

### 方式 2: Makefile 命令（推荐熟手）

```bash
# 查看所有命令
make help

# 常用命令
make dev         # 启动开发环境（前台）
make dev-bg      # 启动开发环境（后台）
make dev-logs    # 查看日志
make dev-down    # 停止开发环境
make health      # 检查健康状态
```

### 方式 3: 直接使用 Docker Compose

```bash
# 开发环境
docker compose -f docker-compose.dev.yml up

# 后台运行
docker compose -f docker-compose.dev.yml up -d

# 查看日志
docker compose -f docker-compose.dev.yml logs -f

# 停止
docker compose -f docker-compose.dev.yml down
```

---

## 💻 开发工作流

### 1. 启动开发环境

```bash
make dev
# 或
./start.sh  # 选择 1) 开发环境
```

你会看到：
```
INFO: Will watch for changes in these directories: ['/app/src']
INFO: Uvicorn running on http://0.0.0.0:8083
INFO: Started reloader process [1] using WatchFiles
```

### 2. 修改代码

在你喜欢的编辑器中编辑代码：
```bash
# 例如修改 Fenbi Engine
code src/services/fenbi_engine.py

# 或使用 vim
vim src/services/fenbi_engine.py
```

### 3. 保存文件

保存后，终端会自动显示：
```
WARNING: WatchFiles detected changes in 'src/services/fenbi_engine.py'. Reloading...
INFO: Shutting down
INFO: Application startup complete.
```

⏱️ **只需 1-2 秒！**

### 4. 测试新功能

```bash
# 打开新终端窗口
curl http://localhost:8086/api/v1/health

# 或访问 API 文档
open http://localhost:8086/docs
```

### 5. 查看日志（可选）

```bash
# 新开一个终端
make dev-logs
# 或
docker compose -f docker-compose.dev.yml logs -f
```

---

## 🔧 开发技巧

### 技巧 1: 使用多个终端窗口

**窗口 1**: 运行服务
```bash
make dev
```

**窗口 2**: 查看日志
```bash
make dev-logs
```

**窗口 3**: 测试 API
```bash
curl http://localhost:8086/api/v1/health
```

### 技巧 2: 快速重启

如果需要完全重启：
```bash
make dev-restart
# 或
docker compose -f docker-compose.dev.yml restart
```

### 技巧 3: 进入容器调试

```bash
make shell
# 或
docker exec -it get-stockdata-api-dev /bin/bash
```

### 技巧 4: 添加临时日志

在代码中添加 print 或 logger：
```python
# 会立即在日志中显示
print(f"[DEBUG] 处理数据: {len(data)} 条")
logger.debug(f"转换耗时: {duration}秒")
```

保存后 1-2 秒即可在日志中看到！

---

## ⚠️ 常见问题

### Q1: 修改代码后没有自动重启？

**检查清单**:
```bash
# 1. 确认使用的是开发环境配置
docker ps | grep get-stockdata-api-dev

# 2. 查看日志是否有错误
make dev-logs

# 3. 检查文件权限
ls -la src/services/fenbi_engine.py

# 4. 手动重启
make dev-restart
```

### Q2: 修改依赖后如何重新构建？

```bash
# 修改了 requirements.txt 需要重新构建
make dev-build
# 或
docker compose -f docker-compose.dev.yml up --build
```

### Q3: 如何清理所有容器？

```bash
make clean
# 或
docker compose -f docker-compose.dev.yml down -v
```

### Q4: 端口被占用怎么办？

```bash
# 查看占用 8086 端口的进程
lsof -i :8086

# 或修改端口（在 .env 文件中）
SERVICE_PORT=8087 make dev
```

---

## 📚 重要文档

- [`README.md`](./README.md) - 项目总览
- [`docs/guides/HOT_RELOAD_GUIDE.md`](./docs/guides/HOT_RELOAD_GUIDE.md) - 热加载详细指南
- [`docs/reports/HOT_RELOAD_TEST_REPORT.md`](./docs/reports/HOT_RELOAD_TEST_REPORT.md) - 测试报告

---

## 🎯 代码规范

### Python 代码风格

- 遵循 PEP 8 规范
- 使用有意义的变量名
- 添加必要的注释和文档字符串

### 提交规范

```bash
# 提交格式
git commit -m "feat: 添加新功能说明"
git commit -m "fix: 修复某个bug"
git commit -m "docs: 更新文档"
git commit -m "refactor: 重构代码"
```

---

## 🤝 贡献流程

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 使用开发环境测试 (`make dev`)
4. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
5. 推送到分支 (`git push origin feature/AmazingFeature`)
6. 开启 Pull Request

---

## 💡 最佳实践

1. **始终使用开发环境开发**: `make dev`
2. **小步提交**: 每次修改一个小功能就提交
3. **观察日志**: 确保每次修改后服务正常重启
4. **测试后提交**: 确保功能正常后再提交代码

---

## 🎉 开始开发吧！

现在你已经了解如何使用开发环境了。记住：

- 🔥 **启动**: `make dev` 或 `./start.sh`
- 📝 **修改**: 编辑代码并保存
- ⏱️ **等待**: 1-2 秒自动重启
- ✅ **测试**: 验证功能是否正常

**祝你编码愉快！** 🚀✨

---

> **需要帮助？** 查看 [docs/guides/HOT_RELOAD_GUIDE.md](./docs/guides/HOT_RELOAD_GUIDE.md) 获取更多详细信息。
