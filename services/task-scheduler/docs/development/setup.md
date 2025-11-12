# 开发环境搭建

## 🛠️ 环境要求

### 系统要求
- Python 3.12+
- Git 2.0+
- Docker 20.0+
- Docker Compose 2.0+

### 推荐工具
- IDE: VS Code / PyCharm
- API测试: Postman / Insomnia
- 数据库: SQLite Browser

## 📦 依赖安装

### Python依赖
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 开发工具
```bash
# 代码格式化
pip install black isort flake8

# 类型检查
pip install mypy

# 测试工具
pip install pytest pytest-asyncio pytest-cov
```

## 🏗️ 项目结构

```
microservice_component/
├── main.py              # 应用入口
├── requirements.txt      # 依赖列表
├── Dockerfile          # 构建文件
├── docker-compose.yml   # 编排文件
├── pyproject.toml       # 项目配置
├── .env.example        # 环境变量模板
├── .gitignore          # Git忽略文件
├── pytest.ini          # 测试配置
├── mypy.ini            # 类型检查配置
├── .flake8             # 代码规范配置
│
├── config/             # 配置文件
├── models/             # 数据模型
├── api/                # API路由
├── service/            # 业务逻辑
├── repository/         # 数据访问
├── plugins/            # 插件系统
├── client/             # 客户端SDK
├── tests/              # 测试文件
└── docs/               # 文档目录
```

## 🔧 开发配置

### 环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
vim .env
```

### 配置文件
```yaml
# config/taskscheduler.yaml
service:
  debug: true
  log_level: DEBUG

api:
  access_log: true

database:
  path: "dev_data/taskscheduler_dev.db"
```

### 开发脚本
```bash
# 启动开发服务
python3 -m uvicorn main:app --reload

# 运行测试
pytest

# 代码检查
flake8 .
black .
mypy .
```

## 🧪 测试环境

### 单元测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_task_service.py

# 生成覆盖率报告
pytest --cov=service --cov-report=html
```

### 集成测试
```bash
# 启动测试环境
docker-compose -f docker-compose.test.yml up -d

# 运行集成测试
pytest tests/integration/

# 清理测试环境
docker-compose -f docker-compose.test.yml down
```

### API测试
```bash
# 启动服务
python3 main.py

# 测试API
curl http://localhost:8080/api/v1/health
```

## 🔍 代码质量

### 代码规范
- 使用Black进行代码格式化
- 使用isort进行导入排序
- 使用flake8进行代码检查
- 使用mypy进行类型检查

### 提交规范
```bash
# 代码检查
pre-commit run

# 运行测试
pytest

# 代码格式化
black .
isort .
```

### Git Hooks
```bash
# 安装pre-commit
pip install pre-commit

# 初始化
pre-commit install
```

## 🐛 调试技巧

### 本地调试
```python
# 启动调试模式
python3 main.py

# 查看日志
tail -f logs/taskscheduler.log
```

### IDE调试
- VS Code: 配置Python调试器
- PyCharm: 配置运行/调试配置
- 设置断点调试

### 日志调试
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("调试信息")
logger.info("一般信息")
logger.error("错误信息")
```

## 📊 监控开发

### 开发监控
```bash
# 启动监控服务
docker-compose --profile monitoring up -d

# 访问监控面板
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000
```

### 性能分析
```bash
# 安装性能分析工具
pip install py-spy

# CPU分析
py-spy record -o profile.raw -- python main.py

# 内存分析
pip install memory_profiler
python -m memory_profiler main.py
```

## 🔄 热重载开发

### 代码热重载
```bash
# 使用uvicorn自动重载
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### 配置热重载
- 支持配置文件自动重新加载
- 监听配置文件变化
- 无需重启服务

## 📚 开发资源

### 文档
- [API文档](http://localhost:8080/docs)
- [架构文档](docs/)
- [代码注释](内联文档)

### 工具链接
- Python官方文档
- FastAPI文档
- APScheduler文档
- Docker文档

### 社区资源
- Stack Overflow
- GitHub Issues
- 开发者论坛

## 🎯 开发最佳实践

### 代码编写
- 遵循PEP 8编码规范
- 编写清晰的函数和类
- 添加适当的注释和文档字符串
- 使用类型提示

### 测试编写
- 编写单元测试覆盖核心功能
- 使用Mock隔离外部依赖
- 编写集成测试验证接口
- 保持测试代码的可维护性

### 版本管理
- 使用语义化版本控制
- 编写清晰的提交信息
- 创建发布说明
- 维护变更日志

### 性能优化
- 避免不必要的计算
- 使用合适的数据结构
- 实现缓存机制
- 监控性能指标

开发环境搭建完成后，您就可以开始为TaskScheduler微服务组件贡献代码了！