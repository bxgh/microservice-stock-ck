# CCI Monitor · Antigravity 开发启动 Prompt

> 这是一组**可直接复制粘贴**到 Antigravity 的 prompt 模板。
> 按 Milestone 顺序使用,每个 prompt 对应一个开发阶段。

---

## 🎬 启动 Prompt(项目初始化)

```
我要开发 CCI Monitor 项目 - 一个基于临界慢化理论的 A 股市场相变监测系统。

请先阅读项目 docs 目录下的三份文档来理解全貌:
1. docs/README.md - 项目简介和快速开始
2. docs/CCI_Monitor_Epic_Stories.md - 完整的 Epic/Story 规划
3. docs/CCI_Monitor_Technical_Spec.md - 技术规范速查

读完后告诉我:
1. 项目的整体架构你理解了吗?
2. 开发路线图有几个 Milestone?
3. Milestone 1 的第一个要做的 Story 是什么?
4. 你有没有任何需要澄清的地方?

不要开始写代码,先确认你理解了文档。
```

---

## 📦 Milestone 1: 地基搭建

### Story 0.1: 项目初始化

```
基于 docs/CCI_Monitor_Epic_Stories.md 中的 Story 0.1,请:

1. 使用 uv 初始化项目,创建 pyproject.toml
2. 创建项目目录结构(参考文档中的项目结构章节)
3. 配置 .gitignore
4. 添加 ruff 和 mypy 的配置
5. 创建基础的 README.md(从 docs/README.md 开始简化版本)

依赖参考 docs/CCI_Monitor_Technical_Spec.md 末尾的"依赖清单"章节。

完成后:
- 运行 `uv sync` 确认无错误
- 告诉我项目结构是否与文档一致
```

### Story 0.2: 配置系统

```
基于 docs/CCI_Monitor_Epic_Stories.md 中的 Story 0.2,请:

1. 创建 config/settings.py,实现 pydantic-settings 的完整 Settings 类
   - 包含 DataSettings, SignalSettings, CCISettings, DatabaseSettings, NotificationSettings
   - 所有字段都要有默认值和类型注解
2. 实现 get_settings() 单例函数
3. 复制 .env.example 到项目根(内容已在 docs 中)
4. 写单元测试验证:
   - 环境变量能正确解析嵌套键(DATA__CACHE_TTL_HOURS)
   - SecretStr 字段不会泄露到日志
   - 默认值生效

注意:嵌套配置使用 __ 作为分隔符(如 DATA__CACHE_TTL_HOURS)。

完成后运行测试确认通过。
```

### Story 0.3: 日志 + Story 0.4: 异常

```
基于 docs/CCI_Monitor_Epic_Stories.md 中的 Story 0.3 和 Story 0.4,请:

1. 实现 backend/src/cci_monitor/core/logger.py
   - 使用 loguru
   - 支持控制台 + 文件双输出
   - 文件按日期滚动,保留 30 天
   
2. 实现 backend/src/cci_monitor/core/exceptions.py
   - 完整异常层级(参考文档 Epic 0.4)
   - 每个异常有唯一 code 字段
   
3. 写简单的使用示例验证两者都能正常工作。

完成后告诉我日志输出的格式示例。
```

### Story 0.5: 数据库 & ORM

```
基于 docs/CCI_Monitor_Epic_Stories.md 中的 Story 0.5,请:

1. 实现 backend/src/cci_monitor/core/database.py
   - 使用 SQLAlchemy 2.0 async
   - 提供 engine、async_session_maker、get_db_session context manager
   
2. 实现 backend/src/cci_monitor/db/models.py
   - CCIRecord 模型
   - AlertRecord 模型
   - DislocationRecord 模型
   - 使用 Mapped[] 新语法
   
3. 初始化 Alembic 并创建首次迁移:
   `alembic init alembic`
   `alembic revision --autogenerate -m "initial tables"`
   
4. 创建 scripts/init_db.py 用于一键初始化

完成后请启动 PostgreSQL (docker-compose up -d postgres) 并运行迁移验证。
```

### Story 1.1 + 1.2: 数据源抽象和 akshare 实现

```
基于 docs/CCI_Monitor_Epic_Stories.md 中的 Story 1.1 和 1.2,请:

1. 实现 DataSource 抽象基类 (backend/src/cci_monitor/data/base.py)
   - 完整接口参考文档
   - async 方法
   - 默认的 fetch_stocks_batch 用 asyncio.gather + Semaphore 控制并发
   
2. 实现 AkshareDataSource (backend/src/cci_monitor/data/akshare_source.py)
   - 所有方法在线程池执行同步 akshare 调用
   - 使用 asyncio.wait_for 强制超时
   - 所有异常包装为项目自定义异常
   - 处理 akshare 返回中文列名的坑(见 Technical Spec)
   
3. 写集成测试(标记 @pytest.mark.integration):
   - 测试能成功获取沪深300近1年数据
   - 测试能获取沪深300成分股列表
   - 测试无效代码抛出 DataSourceEmptyError

关键实现细节参考 docs/CCI_Monitor_Technical_Spec.md 的 "akshare 接口速查" 章节。

完成后运行集成测试(需要网络),告诉我结果。
```

### Story 1.3 + 1.4: 缓存 + 弹性层

```
基于 Story 1.3 和 1.4,请:

1. 实现 Cache 类(backend/src/cci_monitor/data/cache.py)
   - parquet 文件存储
   - meta.json 记录缓存时间
   - 支持 TTL override
   
2. 实现 CachedDataSource 装饰类
   - 包装任意 DataSource 添加缓存
   - 历史数据永久缓存,近期数据 TTL 1h
   
3. 实现 resilience.py(backend/src/cci_monitor/data/resilience.py)
   - 使用 tenacity 的 retry 装饰器
   - 简单断路器实现
   
4. 创建 scripts/clear_cache.py 清理工具

5. 验证完整链路:
   - 第一次请求 → 远程拉取 + 缓存
   - 第二次请求 → 命中缓存
   - 模拟数据源故障 → 断路器打开

完成后告诉我缓存命中率测试结果。
```

---

## 🔬 Milestone 2: 核心指标

### Story 2.1-2.3: 三条信号

```
基于 Story 2.1, 2.2, 2.3,请实现前三条信号。

文件:
- backend/src/cci_monitor/signals/variance.py
- backend/src/cci_monitor/signals/autocorr.py
- backend/src/cci_monitor/signals/skewness.py

关键要求:
- 所有函数返回 pd.DataFrame 或 pd.Series,index 与输入一致
- 数据量不足时抛 InsufficientDataError,不要返回空值
- 完整的 docstring,包含 Args/Returns/Raises/Example

每个信号都写单元测试:
- 常数输入的边界行为
- 已知分布的期望输出
- 数据不足时的异常
```

### Story 2.4: 横截面相关性 ⭐ 核心

```
Story 2.4 是整个项目的核心,请格外仔细实现。

文件: backend/src/cci_monitor/signals/correlation.py

关键要求:
1. 必须使用 numpy 矢量化实现(不要用 pandas.corr() 循环!)
2. 完整代码模板在 docs/CCI_Monitor_Technical_Spec.md 的"横截面相关性矢量化实现"章节
3. 同时实现 compute_directional_correlation(分涨跌日)

性能基准测试:
- 300 股 × 250 天必须 < 3 秒
- 写 pytest-benchmark 测试

正确性测试:
- 独立随机序列 → ρ̄ ≈ 0(±0.1)
- 完全同步序列 → ρ̄ ≈ 1(>0.95)
- 真实沪深300数据 → ρ̄ 在 0.2-0.7 之间

完成后:
1. 运行基准测试,告诉我实际耗时
2. 运行正确性测试,告诉我结果
3. 用真实数据算一遍近 1 年的 ρ̄,可视化看看趋势
```

### Story 2.5: CCI 合成

```
基于 Story 2.5,实现 CCI 合成指数。

文件: backend/src/cci_monitor/signals/cci.py

关键要求:
1. compute_cci 函数返回 CCIResult dataclass
2. 缺失参数使用中性值(参考文档)
3. 权重和必须为 1,否则报错
4. 实现 classify_alert_level 分类函数

测试:
- baseline 场景 CCI 在合理区间
- critical 场景 CCI > 1.3
- 权重不等于 1 时报错
```

### Milestone 2 集成

```
现在把 Milestone 2 的所有组件串起来,实现一个完整的 daily_service:

文件: backend/src/cci_monitor/services/daily_service.py

流程:
1. 拉取今日/最新交易日的数据
2. 计算所有 4 条信号
3. 合成 CCI
4. 写入数据库
5. 返回 CCIResult

同时实现 scripts/run_daily.py 作为 CLI 入口。

验证:
1. 运行 `python scripts/run_daily.py`
2. 查询数据库应该有一条新记录
3. 告诉我计算出的今日 CCI 数值

这就是 Milestone 2 的 Checkpoint。
```

---

## 🏛️ Milestone 3: 分层 + 回测

### L1-L3 分层

```
基于 Story 3.1-3.4 和 3.7,请实现:

1. Layer 抽象基类
2. L1 全市场层(含广度指标)
3. L2 风格层(7 个风格指数)
4. L3 行业层(31 个申万一级行业)
5. 层级错位检测

扩展 daily_service 为多层并行计算。

Checkpoint: 运行 daily_service 应该在数据库中看到 6 层数据(L1+L2有7个+L3有31个)。
```

### Story 4.1-4.2: 历史事件 + 回测引擎

```
基于 Story 4.1 和 4.2:

1. 手工创建 events.yaml(可以先用 ChatGPT 生成初稿,至少 15-20 个事件)
   - 2015 股灾系列
   - 2018 熊市
   - 2020 疫情暴跌和反弹
   - 2021 春节后核心资产崩
   - 2024 微盘股崩
   - 2025-2026 各类事件

2. 实现 BacktestEngine
   - 输入: 起止日期 + 历史 CCI 序列
   - 输出: Precision / Recall / F1 / Lead time
   
3. 创建 scripts/run_backtest.py

跑一次完整回测,告诉我:
- 历史 CCI 曲线的峰值和事件是否对齐
- Precision 和 Recall 分别是多少
```

---

## 🌐 Milestone 4: API 层

```
基于 Epic 7 的 Stories,请:

1. 实现 FastAPI 应用骨架(Story 7.1)
2. 实现核心 API 端点(Story 7.2)
   - 所有端点列表在 docs/CCI_Monitor_Technical_Spec.md 的"API 规范"章节
3. 添加 API Key 认证(简单版,Story 7.3)
4. 写 Docker 配置(Story 0.6)

验证:
- 启动 `docker-compose up -d`
- curl http://localhost:8000/api/v1/cci/latest
- 打开 http://localhost:8000/docs 看 OpenAPI 文档

Checkpoint: 所有主要端点都能正常返回数据。
```

---

## 🎨 Milestone 5: 前端

### Story 5.1: 前端初始化

```
基于 Story 5.1,在 frontend/ 目录下初始化 React 项目:

1. Vite + React 18 + TypeScript
2. 安装依赖(参考 docs/CCI_Monitor_Technical_Spec.md 的 package.json)
3. 配置 TailwindCSS,使用 Volume XI 的完整配色(在 Technical Spec 中)
4. 初始化 shadcn/ui
5. 创建基础路由(Dashboard / Layers / Backtest / Settings)
6. 创建全局布局(Sidebar + TopBar)

运行 `npm run dev`,确认能打开空白页面。
```

### Story 5.2-5.4: 核心页面

```
实现仪表盘主页(Story 5.2-5.4):

1. API 客户端(axios + React Query)
2. CCI 半圆仪表盘组件(SVG)
3. 主页布局:
   - 顶部: CCI 大数字 + 等级徽章
   - 左栏: 仪表盘 + 四分量条形图
   - 右栏: 历史曲线 + ρ̄ 时间序列

视觉要求:
- 严格使用 Volume XI 配色
- 深色主题
- 响应式,适配手机

完成后截图发给我看。
```

### Story 5.5-5.7: 其他页面

```
实现剩余页面:
- Layers 页面(六层热力图 + 详情钻取)
- Backtest 页面(历史 CCI + 事件标记)
- Settings 页面(参数调节)

每个页面完成后给我看截图。
```

---

## ⏰ Milestone 6: 自动化

```
基于 Epic 6,实现:

1. APScheduler 调度器
   - 工作日 17:00 运行 daily_service
   - 每小时健康检查
   
2. 推送通道
   - Server 酱(如果配置了 key)
   - SMTP(如果配置了邮箱)
   - 防骚扰(24h 内同级不重复)

3. 日报生成(文字 + 可选的图片快照)

验证:
- 启动 scheduler 并等待触发
- 或用 `apscheduler` 的手动触发接口立即运行一次
- 确认收到微信/邮件通知
```

---

## 🔧 进度检查 Prompt

### 每周复盘

```
本周我完成了以下 Story: [列出]

请帮我:
1. 检查 docs/CCI_Monitor_Epic_Stories.md 中这些 Story 的验收标准,逐项确认
2. 运行所有相关测试,确认通过
3. 检查代码质量: `ruff check .` 和 `mypy backend/src/`
4. 更新 CHANGELOG.md

告诉我哪些 Story 真正完成,哪些还有遗留项。
```

### 遇到问题时

```
我在实现 Story X.X 时遇到了问题: [描述]

请:
1. 重新阅读 Story X.X 的验收标准
2. 检查相关的 Technical Spec 章节
3. 诊断根本原因
4. 给出修复方案

不要给我长篇解释,直接说该怎么改。
```

### 代码审查

```
请审查 [文件路径] 的代码质量:

检查要点:
1. 是否符合项目代码风格(类型注解、docstring、命名)
2. 是否有性能问题
3. 是否有未处理的异常
4. 测试覆盖是否充分
5. 是否遵循 Technical Spec

给出具体的改进建议,最严重的问题优先。
```

---

## 🚀 部署 Prompt

```
我准备部署到生产环境(VPS / NAS):

1. 检查 docker-compose.yml 配置
2. 生成生产环境的 .env(不要含开发凭据)
3. 配置 Caddy 反向代理 + 自动 HTTPS
4. 写一个 scripts/deploy.sh 部署脚本
5. 写一个 scripts/backup_db.sh 数据库备份脚本

给我一份部署 checklist,包括防火墙、监控、备份的建议。
```

---

## 💡 使用技巧

1. **按 Milestone 顺序** — 不要跳跃,前置依赖必须完成
2. **每个 Story 单独对话** — 上下文清晰,Agent 不容易迷失
3. **让 Agent 读文档** — 而不是把文档内容贴到 prompt 里
4. **遇到歧义让 Agent 问你** — 比让它猜要好
5. **及时运行测试** — 别积累问题到最后

---

## 📚 常用命令速查

```bash
# 开发环境
uv sync                      # 安装依赖
uv run pytest               # 跑测试
uv run ruff check .         # 代码检查
uv run mypy backend/src/    # 类型检查

# 数据库
docker-compose up -d postgres           # 启动 DB
alembic upgrade head                    # 执行迁移
alembic revision --autogenerate -m ""   # 创建迁移

# 应用
uv run uvicorn cci_monitor.api.main:app --reload   # 启动 API
uv run python scripts/run_daily.py                  # 手动计算
uv run python scripts/start_scheduler.py           # 启动调度器

# 前端
npm run dev       # 开发
npm run build     # 生产构建
npm run preview   # 预览构建结果

# Docker
docker-compose up -d           # 启动所有
docker-compose logs -f backend # 查看日志
docker-compose restart backend # 重启
```

---

**祝你开发愉快!有问题随时问 AI Agent。**
