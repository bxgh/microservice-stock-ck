# CCI Monitor · 项目 Epic/Story 规划文档 (v2 完整系统版)

> **项目名称:** A 股相变监测体系 (CCI Monitor)
> **文档版本:** v2.0 — 2026.04.20
> **目标形态:** 完整系统 (数据库 + Web 仪表盘 + 定时任务 + API)
> **数据源策略:** 零预算 (akshare 主源,内建降级)
> **开发节奏:** 6-8 周完成 MVP + 生产化
> **文档定位:** 可被 AI coding agent 直接消化的 PRD + 工程蓝图

---

## 目录

- [项目总览](#项目总览)
- [系统架构图](#系统架构图)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [核心概念词汇表](#核心概念词汇表)
- [Epic 0: 项目基础设施](#epic-0-项目基础设施)
- [Epic 1: 数据基础层](#epic-1-数据基础层)
- [Epic 2: 核心指标引擎](#epic-2-核心指标引擎)
- [Epic 3: 分层监测架构](#epic-3-分层监测架构)
- [Epic 4: 历史回测与校准](#epic-4-历史回测与校准)
- [Epic 5: Web 仪表盘](#epic-5-web-仪表盘)
- [Epic 6: 调度与推送](#epic-6-调度与推送)
- [Epic 7: API 层](#epic-7-api-层)
- [里程碑与迭代计划](#里程碑与迭代计划)
- [Story 验收清单](#story-验收清单)

---

## 项目总览

### 一句话

**基于临界慢化理论,构建一个完整可部署的 A 股市场相变预警系统,提供 Web 仪表盘、REST API 与定时推送。**

### 业务目标

1. 每日自动生成 CCI 数值(0-2 区间),反映市场临界状态
2. 提供三阶预警(关注 / 警戒 / 临界)并自动推送通知
3. 支持六层分层监测(市场 / 风格 / 行业 / 主题 / 龙头 / 个股)
4. Web 仪表盘实时展示当前状态与历史轨迹
5. REST API 供第三方系统接入
6. 历史回测验证信号有效性 (Precision > 60%, Recall > 70%)

### 非功能性需求

- **可用性:** 99% 每日能出日报(全年可容忍 3-4 次接口故障)
- **性能:** 单日全流程计算 < 5 分钟;仪表盘加载 < 3 秒;API P95 < 500ms
- **可扩展性:** 数据源/数据库/消息通道都是可替换组件
- **可维护性:** PEP8 + 类型注解 + 测试覆盖率 ≥ 70%
- **可观测性:** 结构化日志 + 监控指标(Prometheus-ready)

### 范围边界

- ❌ 不做交易决策 — 只输出信号,不产生买卖指令
- ❌ 不做个股选股 — 关注市场结构,不预测个股走势
- ❌ 不做高频 — 最小时间粒度为日度
- ❌ 不做用户账户体系 — 单用户个人部署,如需多用户再加 Epic 8

---

## ⭐ 关键依赖声明:横截面相关性 ρ̄ 是项目基石

虽然 CCI 监测体系由四条信号合成,但**横截面相关性 ρ̄(Story 2.4)在技术和业务上都是整个项目的基石**:

### 技术层面
- CCI 合成公式的 **α、β、γ、δ 四个分量全部**依赖 ρ̄
- 六层分层监测每一层的 CCI 都基于该层的 ρ̄
- 历史回测需要完整的历史 ρ̄ 序列
- 仪表盘的核心图表就是 ρ̄ 时间序列

### 业务层面
- ρ̄ 是 A 股临界预警中**最敏感的单一信号**(详见 Volume XI 研究)
- 其他三条信号(方差/自相关/偏度)都无法替代 ρ̄ 的独特维度

### 开发启示
- **Story 2.4 的完成度决定整个项目的上限** — 必须按 MVP 最高优先级对待
- 性能要求硬:300 股 × 250 天计算必须 < 3 秒,否则整个系统无法每日运行
- 正确性要求严:所有单元测试 + 真实数据验证必须全过,否则下游全部失真
- **开发时建议留出 1-2 天专注投入**,不要碎片化

---

## MVP 优先级明确声明

按开发顺序(严格不可跳跃):

| 优先级 | 模块 | 原因 |
|---|---|---|
| **P0 必需** | Epic 0 基础设施 | 配置、日志、异常、DB、Docker — 没有这些上层跑不起来 |
| **P0 必需** | Story 1.1-1.4 数据层 | akshare 接入 + 缓存 + 弹性 — 没有数据无法计算 |
| **⭐ P0 基石** | **Story 2.4 横截面相关性** | **整个 CCI 体系的数学基础,阻塞所有下游 Story** |
| **P0 必需** | Story 2.1/2.2/2.3 其他三条信号 | CCI 完整度需要 |
| **P0 必需** | Story 2.5 CCI 合成 | 将四条信号合成输出 |
| **P0 必需** | Story 2.6 daily_service | 把整条流水线跑通 |
| **P1 高优先级** | Epic 3 分层监测(L1-L3) | 单层 CCI 价值有限,需要分层对比才有意义 |
| **P1 高优先级** | Epic 4 历史回测 | 验证信号有效性,否则无信任度 |
| **P2 重要** | Epic 7 API 层 | 解耦前后端 |
| **P2 重要** | Epic 5 Web 仪表盘 | 可见性,用户入口 |
| **P2 重要** | Epic 6 自动化推送 | 每日自动运行 + 警报 |
| **P3 延后** | Epic 3 L4-L6 层 | 主题/龙头/个股层复杂度高,价值递减 |

---

## 系统架构图

```
┌────────────────────────────────────────────────────────────────┐
│                         用户 / 浏览器 / 微信                      │
└────────────────────────────────────────────────────────────────┘
              │                       │                    │
              ▼                       ▼                    ▼
┌──────────────────┐    ┌──────────────────┐   ┌─────────────────┐
│   Web 仪表盘      │    │    REST API      │   │   推送通道       │
│  (Next.js/React)  │◄───│   (FastAPI)      │   │ (Server酱/SMTP) │
└──────────────────┘    └──────────────────┘   └─────────────────┘
         │                        │                      ▲
         └────────────────────────┼──────────────────────┘
                                  ▼
                    ┌──────────────────────────┐
                    │      应用服务层           │
                    │  (Business Logic)        │
                    └──────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   信号引擎       │    │   分层监测       │    │   回测引擎       │
│  (Signals)      │    │   (Layers)      │    │  (Backtest)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  ▼
                    ┌──────────────────────────┐
                    │        数据层             │
                    │   (Data Source + Cache)  │
                    └──────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │  Redis (缓存)    │    │  akshare API    │
│  (持久化/时序)    │    │  (可选,MVP可跳过) │   │  (数据源)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │    APScheduler           │
                    │  (每日定时任务)            │
                    └──────────────────────────┘
```

**架构原则:**
1. **分层清晰** — 数据/指标/业务/接口/UI 严格分层,不跨层调用
2. **依赖倒置** — 上层依赖接口而非具体实现(便于替换数据源)
3. **异步优先** — API 层用 async/await,后台任务用 APScheduler
4. **事件驱动** — 状态升级触发推送(不轮询)

---

## 技术栈

### 核心依赖

| 类别 | 选型 | 理由 |
|---|---|---|
| **语言** | Python 3.11+ | 类型系统完善,性能好 |
| **数据获取** | akshare (主) | 免费开源覆盖 A 股主流数据 |
| **数据处理** | pandas / numpy / scipy | 业内标配 |
| **数据库** | PostgreSQL + SQLAlchemy 2.0 | 时序支持好,事务可靠 |
| **缓存** | diskcache (MVP) → Redis (扩展) | 先文件缓存降低部署复杂度 |
| **ORM** | SQLAlchemy 2.0 (async) | 原生异步支持 |
| **数据库迁移** | Alembic | SQLAlchemy 配套 |
| **Web 框架** | FastAPI | 异步、类型、自动文档 |
| **前端** | **React + Vite + TailwindCSS + shadcn/ui** | 组件化、主题化容易 |
| **前端图表** | Recharts + D3 | 与 Volume XI 视觉风格对齐 |
| **前端状态管理** | Zustand / React Query | 轻量但足够 |
| **任务调度** | APScheduler | 进程内调度,部署简单 |
| **推送** | Server 酱 (微信) + SMTP (邮件) | 微信零成本 |
| **日志** | loguru | 比 logging 更友好 |
| **配置** | pydantic-settings | 类型安全 |
| **测试** | pytest + pytest-asyncio + pytest-cov | 业内标准 |
| **代码质量** | ruff + mypy | 快速且严格 |
| **容器化** | Docker + docker-compose | 一键部署 |

### 部署方案

**推荐方案 A: 单机部署 (MVP)**
- 一台 VPS / NAS / 本地机器
- docker-compose 启动 PostgreSQL + 后端 + 前端 + 调度器
- 使用 Caddy 做反向代理和自动 HTTPS

**推荐方案 B: 免部署本地模式**
- 直接在开发机运行,无 Docker
- 适合个人使用,随开随用

---

## 项目结构

```
cci-monitor/
├── README.md
├── pyproject.toml                   # 项目配置
├── .env.example                     # 配置模板
├── .gitignore
├── docker-compose.yml               # 容器化部署
├── Dockerfile.backend
├── Dockerfile.frontend
│
├── docs/                            # 文档
│   ├── CCI_Monitor_Epic_Stories.md
│   ├── CCI_Monitor_Technical_Spec.md
│   └── theory.md
│
├── config/
│   ├── __init__.py
│   ├── settings.py                  # 全局配置
│   └── constants.py                 # 常量
│
├── backend/                         # 后端
│   ├── src/cci_monitor/
│   │   ├── __init__.py
│   │   │
│   │   ├── core/                    # 基础设施
│   │   │   ├── logger.py
│   │   │   ├── exceptions.py
│   │   │   └── database.py          # DB 连接与会话
│   │   │
│   │   ├── db/                      # 数据库模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── models.py            # ORM 模型
│   │   │
│   │   ├── data/                    # Epic 1
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # DataSource 抽象
│   │   │   ├── akshare_source.py    # akshare 实现
│   │   │   ├── cache.py
│   │   │   ├── resilience.py        # 重试/降级/断路器
│   │   │   └── models.py            # 数据模型 (Pydantic)
│   │   │
│   │   ├── signals/                 # Epic 2
│   │   │   ├── __init__.py
│   │   │   ├── variance.py
│   │   │   ├── autocorr.py
│   │   │   ├── skewness.py
│   │   │   ├── correlation.py       # 核心
│   │   │   └── cci.py
│   │   │
│   │   ├── layers/                  # Epic 3
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── layer_1_market.py
│   │   │   ├── layer_2_style.py
│   │   │   ├── layer_3_industry.py
│   │   │   ├── layer_4_theme.py
│   │   │   ├── layer_5_leader.py
│   │   │   ├── layer_6_stock.py
│   │   │   └── dislocation.py       # 层级错位检测
│   │   │
│   │   ├── backtest/                # Epic 4
│   │   │   ├── __init__.py
│   │   │   ├── events.yaml
│   │   │   ├── engine.py
│   │   │   └── metrics.py
│   │   │
│   │   ├── services/                # 业务服务层
│   │   │   ├── __init__.py
│   │   │   ├── daily_service.py     # 每日计算服务
│   │   │   ├── alert_service.py     # 预警服务
│   │   │   └── report_service.py    # 报告生成
│   │   │
│   │   ├── api/                     # Epic 7
│   │   │   ├── __init__.py
│   │   │   ├── main.py              # FastAPI app
│   │   │   ├── deps.py              # 依赖注入
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── cci.py           # /api/v1/cci
│   │   │   │   ├── layers.py        # /api/v1/layers
│   │   │   │   ├── backtest.py      # /api/v1/backtest
│   │   │   │   └── system.py        # /api/v1/system
│   │   │   └── schemas.py           # Pydantic 响应模型
│   │   │
│   │   ├── scheduler/               # Epic 6
│   │   │   ├── __init__.py
│   │   │   ├── main.py              # 调度器入口
│   │   │   ├── jobs.py              # 任务定义
│   │   │   └── notifier.py          # 推送
│   │   │
│   │   └── utils/
│   │       ├── dates.py             # 交易日工具
│   │       └── formatting.py        # 格式化
│   │
│   ├── alembic/                     # 数据库迁移
│   │   ├── env.py
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   └── integration/
│   │
│   └── scripts/                     # 运行脚本
│       ├── run_daily.py             # 手动触发每日计算
│       ├── run_backtest.py          # 手动触发回测
│       ├── start_api.py             # 启动 API 服务
│       ├── start_scheduler.py       # 启动调度器
│       └── init_db.py               # 初始化数据库
│
├── frontend/                        # 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   │
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── router.tsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx        # 主页 - 实时概览
│   │   │   ├── Layers.tsx           # 分层监测详情
│   │   │   ├── Backtest.tsx         # 历史回测
│   │   │   └── Settings.tsx         # 设置
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn 组件
│   │   │   ├── charts/              # 图表组件
│   │   │   │   ├── CCIGauge.tsx     # 半圆仪表盘
│   │   │   │   ├── CCIHistory.tsx   # 历史曲线
│   │   │   │   ├── LayerHeatmap.tsx # 分层热力图
│   │   │   │   ├── RhoBarChart.tsx  # ρ̄ 时间序列
│   │   │   │   └── ComponentBars.tsx # 四分量
│   │   │   └── layout/
│   │   │       ├── Sidebar.tsx
│   │   │       └── TopBar.tsx
│   │   │
│   │   ├── services/
│   │   │   └── api.ts               # API 客户端
│   │   ├── hooks/
│   │   ├── store/                   # Zustand
│   │   └── lib/
│   │       ├── theme.ts             # 主题 (对齐 Vol XI 配色)
│   │       └── utils.ts
│   │
│   └── public/
│
└── deploy/                          # 部署资源
    ├── caddy/Caddyfile              # 反向代理配置
    ├── nginx/                       # 备选
    └── systemd/                     # 备选(非 Docker)
```

---

## 核心概念词汇表

| 中文 | 英文/代码名 | 定义 |
|---|---|---|
| **横截面相关性** | `rho_bar` | 多只股票两两收益率相关系数的均值 |
| **CCI 合成指数** | `cci` | 四分量加权得到的综合临界指标,范围 0-2 |
| **分量 α / β / γ / δ** | `alpha_component` / `beta_component` / `gamma_component` / `delta_component` | CCI 的四个加权分量 |
| **信号 ① 方差** | `variance_rise` | 短期/长期波动率比值信号 |
| **信号 ② 自相关** | `autocorrelation` | AR(1) 系数信号 |
| **信号 ③ 偏度** | `skewness_flip` | 收益率分布偏度信号 |
| **信号 ④ 横截面** | `cross_correlation` | 横截面相关性信号(最核心) |
| **一阶关注** | `alert_level_1` | CCI 0.7-1.0 |
| **二阶警戒** | `alert_level_2` | CCI 1.0-1.3 |
| **三阶临界** | `alert_level_3` | CCI > 1.3 |
| **监测层级 L1-L6** | `layer_1` … `layer_6` | 六层监测架构 |
| **介质类型** | `medium_type` | jelly / deep_water / shallow / resonant / frozen |
| **形态 A/B/C** | `pattern_a_rally` / `pattern_b_crash` / `pattern_c_crowding` | 横截面相关性的三种形态 |
| **层级错位** | `layer_dislocation` | 跨层级的异常信号组合 |

---

## Epic 0: 项目基础设施

### Epic 目标

建立项目的**基础设施层**:依赖管理、配置、日志、异常、数据库连接、Docker 环境。
没有这一步,上面的代码跑不起来。

### Stories

---

#### Story 0.1: 项目初始化与依赖管理

**As a** 开发者
**I want** 一个标准化的 Python 项目骨架
**So that** 所有开发者开箱即用,依赖版本一致

**技术实现:**

- 使用 `uv` (推荐) 或 `poetry` 管理依赖
- `pyproject.toml` 完整声明项目元数据
- 区分生产依赖 / 开发依赖 / 可选依赖

**验收标准:**
- [ ] `uv sync` 或 `poetry install` 一键安装所有依赖
- [ ] `pyproject.toml` 中有完整的项目描述、作者、许可证
- [ ] 有 `[tool.ruff]` 和 `[tool.mypy]` 的配置
- [ ] 有 `.python-version` 或类似的 Python 版本固定
- [ ] `.gitignore` 覆盖 `.venv/` `data/` `logs/` `.env` 等

**预计工时:** 2 小时

---

#### Story 0.2: 配置管理系统

**As a** 开发者
**I want** 类型安全的配置系统
**So that** 所有参数都有明确的类型和默认值,环境切换不出错

**技术实现:**

```python
# config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field
from pathlib import Path
from typing import Literal

class DataSettings(BaseSettings):
    primary_source: Literal["akshare", "tushare"] = "akshare"
    tushare_token: SecretStr | None = None
    cache_dir: Path = Path("data/cache")
    cache_ttl_hours: int = 24
    request_timeout: int = 30
    max_retries: int = 3

class SignalSettings(BaseSettings):
    variance_short_window: int = 20
    variance_long_window: int = 60
    variance_threshold: float = 1.5
    autocorr_window: int = 60
    autocorr_threshold: float = 0.15
    skew_window: int = 60
    skew_threshold: float = 1.0
    correlation_window: int = 20
    correlation_stock_count: int = 300

class CCISettings(BaseSettings):
    alpha_weight: float = 0.4
    beta_weight: float = 0.3
    gamma_weight: float = 0.2
    delta_weight: float = 0.1
    alert_threshold_l1: float = 0.7
    alert_threshold_l2: float = 1.0
    alert_threshold_l3: float = 1.3

class DatabaseSettings(BaseSettings):
    url: str = "postgresql+asyncpg://cci:cci@localhost:5432/cci_monitor"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10

class NotificationSettings(BaseSettings):
    server_chan_key: SecretStr | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    smtp_to: str | None = None
    enable_daily_report: bool = True

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
    
    env: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    data: DataSettings = DataSettings()
    signal: SignalSettings = SignalSettings()
    cci: CCISettings = CCISettings()
    database: DatabaseSettings = DatabaseSettings()
    notification: NotificationSettings = NotificationSettings()

# 单例
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**`.env.example`:**

```bash
# ==== 环境 ====
ENV=dev
LOG_LEVEL=INFO

# ==== 数据源 ====
DATA__PRIMARY_SOURCE=akshare
DATA__CACHE_DIR=data/cache

# ==== 数据库 ====
DATABASE__URL=postgresql+asyncpg://cci:cci@localhost:5432/cci_monitor

# ==== 推送(可选)====
NOTIFICATION__SERVER_CHAN_KEY=
NOTIFICATION__SMTP_HOST=
NOTIFICATION__SMTP_USER=
NOTIFICATION__SMTP_TO=
```

**验收标准:**
- [ ] 支持嵌套配置(`DATA__PRIMARY_SOURCE` 语法)
- [ ] 敏感配置使用 `SecretStr`
- [ ] `get_settings()` 是 `lru_cache` 单例
- [ ] 有对应的单元测试(mock 环境变量)
- [ ] `.env.example` 覆盖所有可配置项

**预计工时:** 3 小时

---

#### Story 0.3: 日志系统

**技术实现:**

```python
# backend/src/cci_monitor/core/logger.py
from loguru import logger
from config.settings import get_settings
import sys

def setup_logging():
    settings = get_settings()
    logger.remove()  # 清除默认
    
    # 控制台输出
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level:8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "{message}",
    )
    
    # 文件输出(按日期滚动)
    logger.add(
        "logs/cci_{time:YYYY-MM-DD}.log",
        level=settings.log_level,
        rotation="00:00",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:8} | "
               "{name}:{function}:{line} | {message}",
    )
    
    # 生产环境错误单独文件
    if settings.env == "prod":
        logger.add(
            "logs/cci_error_{time:YYYY-MM-DD}.log",
            level="ERROR",
            rotation="00:00",
            retention="90 days",
        )

# 便捷导出
__all__ = ["logger", "setup_logging"]
```

**验收标准:**
- [ ] 启动时一次性配置
- [ ] 日志文件按日期滚动
- [ ] 生产环境错误日志单独文件
- [ ] 支持结构化字段(`logger.info("X", x=1, y=2)`)

**预计工时:** 2 小时

---

#### Story 0.4: 异常层级

**技术实现:**

```python
# backend/src/cci_monitor/core/exceptions.py

class CCIError(Exception):
    """项目所有异常的基类."""
    code: str = "CCI_ERROR"
    
    def __init__(self, message: str, **context):
        super().__init__(message)
        self.context = context

# === 数据源异常 ===
class DataSourceError(CCIError):
    code = "DATA_SOURCE_ERROR"

class DataSourceEmptyError(DataSourceError):
    code = "DATA_SOURCE_EMPTY"

class DataSourceTimeoutError(DataSourceError):
    code = "DATA_SOURCE_TIMEOUT"

class DataSourceUnavailableError(DataSourceError):
    code = "DATA_SOURCE_UNAVAILABLE"

class DataSourceRateLimitError(DataSourceError):
    code = "DATA_SOURCE_RATE_LIMIT"

# === 信号异常 ===
class SignalError(CCIError):
    code = "SIGNAL_ERROR"

class InsufficientDataError(SignalError):
    code = "INSUFFICIENT_DATA"

# === 配置异常 ===
class ConfigurationError(CCIError):
    code = "CONFIG_ERROR"

# === 数据库异常 ===
class DatabaseError(CCIError):
    code = "DATABASE_ERROR"
```

**验收标准:**
- [ ] 所有异常有唯一 code 字段(用于 API 响应)
- [ ] 支持 context 字段传递额外信息

**预计工时:** 1 小时

---

#### Story 0.5: 数据库连接与 ORM 基础

**技术实现:**

```python
# backend/src/cci_monitor/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager
from config.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database.url,
    echo=settings.database.echo,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

@asynccontextmanager
async def get_db_session() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**ORM 模型示例(为 CCI 结果):**

```python
# backend/src/cci_monitor/db/models.py
from sqlalchemy import String, Float, Integer, Date, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date, datetime
from backend.src.cci_monitor.core.database import Base

class CCIRecord(Base):
    __tablename__ = "cci_records"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    layer_id: Mapped[int] = mapped_column(Integer, index=True)
    
    cci: Mapped[float]
    alpha: Mapped[float]
    beta: Mapped[float]
    gamma: Mapped[float]
    delta: Mapped[float]
    
    alert_level: Mapped[int]
    alert_label: Mapped[str] = mapped_column(String(20))
    
    # 诊断字段
    market_rho: Mapped[float | None]
    resonant_rho: Mapped[float | None]
    deep_rho: Mapped[float | None]
    delta_rho: Mapped[float | None]
    up_down_ratio: Mapped[float | None]
    
    # 扩展存储
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    
    computed_at: Mapped[datetime]
    
    __table_args__ = (
        UniqueConstraint("date", "layer_id", name="uq_date_layer"),
        Index("ix_date_layer", "date", "layer_id"),
    )

class AlertRecord(Base):
    __tablename__ = "alert_records"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    triggered_at: Mapped[datetime] = mapped_column(index=True)
    alert_level: Mapped[int]
    layer_id: Mapped[int]
    cci_value: Mapped[float]
    message: Mapped[str]
    context_json: Mapped[dict | None] = mapped_column(JSON)
    notified: Mapped[bool] = mapped_column(default=False)

class DislocationRecord(Base):
    __tablename__ = "dislocation_records"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(index=True)
    dislocation_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[int]
    involved_layers: Mapped[list[int]] = mapped_column(JSON)
    description: Mapped[str]
```

**验收标准:**
- [ ] 使用 async SQLAlchemy 2.0 语法
- [ ] 所有模型有必要的索引
- [ ] 有 Alembic 初始化迁移
- [ ] 提供 `init_db.py` 脚本用于初始化

**预计工时:** 4 小时

---

#### Story 0.6: Docker 化

**技术实现:**

```yaml
# docker-compose.yml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: cci
      POSTGRES_PASSWORD: cci
      POSTGRES_DB: cci_monitor
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cci"]
      interval: 10s
  
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend:/app
      - ./data:/app/data
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    command: uvicorn cci_monitor.api.main:app --host 0.0.0.0 --port 8000 --reload
  
  scheduler:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    command: python scripts/start_scheduler.py
  
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      VITE_API_URL: http://localhost:8000
  
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/caddy/Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - backend
      - frontend

volumes:
  pg_data:
  caddy_data:
  caddy_config:
```

**验收标准:**
- [ ] `docker-compose up -d` 一键启动所有服务
- [ ] 服务之间通过健康检查正确依赖
- [ ] 数据持久化(重启后数据不丢)
- [ ] Caddy 自动 HTTPS(生产部署)

**预计工时:** 4 小时

**依赖:** 0.1-0.5

---

## Epic 1: 数据基础层

### Epic 目标

建立**稳定可替换**的数据获取层。akshare 不稳定是常态,架构必须假设它会故障。

### Stories

---

#### Story 1.1: DataSource 抽象基类

**技术实现:**

```python
# backend/src/cci_monitor/data/base.py
from abc import ABC, abstractmethod
from datetime import date
import pandas as pd

class DataSource(ABC):
    """数据源抽象基类."""
    
    name: str
    
    @abstractmethod
    async def fetch_index_daily(
        self, symbol: str, 
        start_date: date, 
        end_date: date | None = None
    ) -> pd.DataFrame:
        """
        获取指数日度行情.
        
        Returns:
            DataFrame with columns: 
                - date (pd.Timestamp)
                - open, high, low, close, volume (float)
                - change_pct (float, 百分比如 1.5 表示 1.5%)
        """
        ...
    
    @abstractmethod
    async def fetch_index_components(self, index_code: str) -> list[str]:
        """
        获取指数成分股代码列表.
        
        Args:
            index_code: '000300' / '000905' / '000852' 等
        
        Returns:
            股票代码列表,带市场后缀如 ['600519.SH', '000001.SZ']
        """
        ...
    
    @abstractmethod
    async def fetch_stock_daily(
        self, code: str, 
        start_date: date, 
        end_date: date | None = None
    ) -> pd.DataFrame:
        """获取单只股票日度数据,格式同 fetch_index_daily."""
        ...
    
    async def fetch_stocks_batch(
        self, codes: list[str],
        start_date: date,
        end_date: date | None = None,
        concurrency: int = 5,
    ) -> pd.DataFrame:
        """
        并发批量获取,返回宽表.
        
        Returns:
            DataFrame: index=date, columns=codes, values=change_pct
        """
        import asyncio
        semaphore = asyncio.Semaphore(concurrency)
        
        async def fetch_one(code: str):
            async with semaphore:
                try:
                    df = await self.fetch_stock_daily(code, start_date, end_date)
                    return code, df
                except Exception as e:
                    logger.warning(f"Failed to fetch {code}: {e}")
                    return code, pd.DataFrame()
        
        results = await asyncio.gather(*[fetch_one(c) for c in codes])
        # 合并为宽表
        series_dict = {}
        for code, df in results:
            if not df.empty:
                series_dict[code] = df.set_index("date")["change_pct"]
        return pd.DataFrame(series_dict)
    
    @abstractmethod
    async def is_healthy(self) -> bool:
        """健康检查."""
        ...
```

**验收标准:**
- [ ] 接口规范使用 async/await
- [ ] 批量方法默认实现并发调用
- [ ] 有完整的 docstring 包含返回格式

**预计工时:** 2 小时

---

#### Story 1.2: akshare 数据源实现

**技术实现:**

```python
# backend/src/cci_monitor/data/akshare_source.py
import akshare as ak
import asyncio
import pandas as pd
from datetime import date, datetime
from ..core.exceptions import DataSourceEmptyError, DataSourceTimeoutError, DataSourceError
from .base import DataSource
from ..core.logger import logger

class AkshareDataSource(DataSource):
    name = "akshare"
    
    async def _run_sync(self, func, *args, **kwargs):
        """在线程池中执行同步 akshare 调用."""
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, lambda: func(*args, **kwargs)),
                timeout=30,
            )
        except asyncio.TimeoutError:
            raise DataSourceTimeoutError(f"akshare timeout: {func.__name__}")
        except Exception as e:
            raise DataSourceError(f"akshare failed: {e}", exception=str(e))
    
    async def fetch_index_daily(self, symbol, start_date, end_date=None):
        end_date = end_date or date.today()
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        df = await self._run_sync(
            ak.stock_zh_index_daily_em,
            symbol=symbol,
            start_date=start_str,
            end_date=end_str,
        )
        
        if df.empty:
            raise DataSourceEmptyError(f"no data for {symbol}")
        
        # 标准化字段
        df = df.rename(columns=str.lower)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df["change_pct"] = df["close"].pct_change() * 100
        
        return df[["date", "open", "high", "low", "close", "volume", "change_pct"]]
    
    async def fetch_index_components(self, index_code):
        df = await self._run_sync(ak.index_stock_cons_sina, symbol=index_code)
        if df.empty:
            raise DataSourceEmptyError(f"no components for {index_code}")
        
        codes = []
        for code in df["code"].tolist():
            suffix = ".SH" if code.startswith("6") else ".SZ"
            codes.append(f"{code}{suffix}")
        return codes
    
    async def fetch_stock_daily(self, code, start_date, end_date=None):
        end_date = end_date or date.today()
        pure_code = code.split(".")[0] if "." in code else code
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        df = await self._run_sync(
            ak.stock_zh_a_hist,
            symbol=pure_code,
            period="daily",
            start_date=start_str,
            end_date=end_str,
            adjust="qfq",
        )
        
        if df.empty:
            raise DataSourceEmptyError(f"no data for {code}")
        
        # 标准化字段(注意 akshare 中文列名)
        column_mapping = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "涨跌幅": "change_pct",
        }
        df = df.rename(columns=column_mapping)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        
        return df[["date", "open", "high", "low", "close", "volume", "change_pct"]]
    
    async def is_healthy(self):
        try:
            # 拉取一个小样本验证
            df = await self.fetch_index_daily(
                "sh000300",
                date.today() - pd.Timedelta(days=7),
                date.today(),
            )
            return not df.empty
        except Exception:
            return False
```

**验收标准:**
- [ ] 所有异常被包装为项目异常
- [ ] 使用 asyncio.wait_for 强制超时
- [ ] 批量接口(fetch_stocks_batch)使用信号量控制并发
- [ ] 有集成测试(需要网络)

**预计工时:** 6-8 小时

---

#### Story 1.3: 缓存层

**技术实现:**

```python
# backend/src/cci_monitor/data/cache.py
from pathlib import Path
import pandas as pd
import hashlib
import json
from datetime import datetime, date, timedelta

class Cache:
    """基于 parquet 文件的本地缓存."""
    
    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _key(self, namespace: str, **params) -> str:
        """生成缓存键."""
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        hash_str = hashlib.md5(sorted_params.encode()).hexdigest()[:8]
        return f"{namespace}_{hash_str}"
    
    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.parquet"
    
    def _meta_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.meta.json"
    
    def get(self, namespace: str, ttl_override: timedelta | None = None, **params) -> pd.DataFrame | None:
        key = self._key(namespace, **params)
        path = self._path(key)
        meta_path = self._meta_path(key)
        
        if not path.exists() or not meta_path.exists():
            return None
        
        # 检查 TTL
        meta = json.loads(meta_path.read_text())
        cached_at = datetime.fromisoformat(meta["cached_at"])
        effective_ttl = ttl_override or self.ttl
        if datetime.now() - cached_at > effective_ttl:
            return None
        
        try:
            return pd.read_parquet(path)
        except Exception:
            return None
    
    def set(self, namespace: str, df: pd.DataFrame, **params):
        key = self._key(namespace, **params)
        path = self._path(key)
        meta_path = self._meta_path(key)
        
        df.to_parquet(path, index=False)
        meta_path.write_text(json.dumps({
            "cached_at": datetime.now().isoformat(),
            "params": params,
            "rows": len(df),
        }, default=str))
    
    def clear(self, namespace: str | None = None):
        pattern = f"{namespace}_*" if namespace else "*"
        for f in self.cache_dir.glob(pattern):
            f.unlink()
```

**缓存策略实现:**

```python
# CachedDataSource 装饰
class CachedDataSource(DataSource):
    """给任何 DataSource 加上缓存."""
    
    def __init__(self, inner: DataSource, cache: Cache):
        self.inner = inner
        self.cache = cache
        self.name = f"cached({inner.name})"
    
    async def fetch_index_daily(self, symbol, start_date, end_date=None):
        end_date = end_date or date.today()
        
        # 历史数据永久缓存,近期数据短期缓存
        is_recent = (date.today() - end_date).days < 3
        ttl = timedelta(hours=1) if is_recent else timedelta(days=30)
        
        cached = self.cache.get(
            "index_daily",
            ttl_override=ttl,
            symbol=symbol,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
        )
        if cached is not None:
            logger.debug(f"cache hit: index_daily {symbol}")
            return cached
        
        df = await self.inner.fetch_index_daily(symbol, start_date, end_date)
        self.cache.set(
            "index_daily", df,
            symbol=symbol,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
        )
        return df
    
    # 其他方法类似...
```

**验收标准:**
- [ ] 缓存命中 < 100ms
- [ ] 历史数据永久缓存,近期数据 TTL 1 小时
- [ ] 文件损坏时自动失效
- [ ] 提供 `scripts/clear_cache.py`

**预计工时:** 4 小时

---

#### Story 1.4: 弹性层(降级/重试/断路器)

**As a** 运维者
**I want** 数据源故障时系统仍能运行
**So that** akshare 挂了不影响整体可用性

**技术实现:**

```python
# backend/src/cci_monitor/data/resilience.py
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ..core.exceptions import DataSourceTimeoutError, DataSourceRateLimitError
from ..core.logger import logger

def with_retry(func):
    """重试装饰器: 超时或限流自动重试."""
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((DataSourceTimeoutError, DataSourceRateLimitError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying {func.__name__} (attempt {retry_state.attempt_number})"
        ),
        reraise=True,
    )(func)

class CircuitBreaker:
    """简单断路器,防止雪崩."""
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = None
        self.state: Literal["closed", "open", "half_open"] = "closed"
    
    def record_success(self):
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.error("Circuit breaker opened")
    
    def can_attempt(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "half_open"
                return True
            return False
        return True  # half_open: 允许试探
```

**验收标准:**
- [ ] 超时错误自动重试(指数退避)
- [ ] 连续 5 次失败触发断路器
- [ ] 断路器 60 秒后进入 half_open 尝试恢复

**预计工时:** 3 小时

---

## Epic 2: 核心指标引擎

### Epic 目标

实现四条预警信号 + CCI 合成指数的计算逻辑。**每条信号独立可测,可单独验证。**

### ⚠️ 关键依赖说明

**Story 2.4(横截面相关性)是整个项目的数学基石**,以下全部模块依赖它:
- CCI 合成公式的 α、β、γ、δ 四个分量都需要 ρ̄
- 六层分层监测每一层都需要计算 ρ̄
- 历史回测需要 ρ̄ 序列才能复现 CCI
- 仪表盘的核心图表之一就是 ρ̄ 时间序列

**如果 Story 2.4 未实现,整个项目等于没有开始。** 必须作为 MVP 最高优先级项目。

### Stories

---

#### Story 2.1: 信号 ① 波动率方差上升

**As a** 开发者
**I want** 实现波动率方差比信号
**So that** 可以检测市场临界前的方差放大现象

**技术实现:**

```python
# backend/src/cci_monitor/signals/variance.py
from __future__ import annotations
import numpy as np
import pandas as pd
from ..core.exceptions import InsufficientDataError

def compute_variance_rise(
    returns: pd.Series,
    short_window: int = 20,
    long_window: int = 60,
    threshold: float = 1.5,
    persist_days: int = 5,
) -> pd.DataFrame:
    """
    计算波动率方差上升信号.
    
    逻辑: 接近临界时,系统恢复变慢,相同外力激起更大振幅.
    表现为短期波动率超过长期基准.
    
    Args:
        returns: 日收益率序列(%), index 为 date
        short_window: 短期窗口, 默认 20 日
        long_window: 长期基准窗口, 默认 60 日
        threshold: 比值触发阈值
        persist_days: 连续触发天数要求
    
    Returns:
        DataFrame with columns:
            - short_vol: 短期年化波动率(%)
            - long_vol:  长期年化波动率(%)
            - ratio:     short_vol / long_vol
            - triggered: 是否触发(ratio > threshold 持续 persist_days 日)
    
    Raises:
        InsufficientDataError: 如果 returns 长度小于 long_window
    """
    if len(returns) < long_window:
        raise InsufficientDataError(
            f"need at least {long_window} bars, got {len(returns)}"
        )
    
    short_vol = returns.rolling(short_window).std() * np.sqrt(252)
    long_vol = returns.rolling(long_window).std() * np.sqrt(252)
    ratio = short_vol / long_vol
    
    # 连续 persist_days 日大于阈值才算触发
    above = (ratio > threshold).astype(int)
    persist = above.rolling(persist_days).sum() >= persist_days
    
    return pd.DataFrame({
        'short_vol': short_vol,
        'long_vol': long_vol,
        'ratio': ratio,
        'triggered': persist,
    })
```

**验收标准:**
- [ ] 输入长度不足抛 `InsufficientDataError`
- [ ] 输出 DataFrame 的 index 与输入一致
- [ ] 前 `long_window` 行的输出为 NaN(符合 rolling 语义)
- [ ] 单元测试:
  - 常数收益率 → ratio 稳定在 1.0 附近,无触发
  - 波动突然放大 3 倍 → 5 日后触发
  - 长度正好等于 long_window → 最后一行有值
- [ ] 性能:1000 个数据点计算 < 10ms

**预计工时:** 2 小时

**依赖:** Epic 0

---

#### Story 2.2: 信号 ② 自相关性

**As a** 开发者
**I want** 实现 AR(1) 自相关信号
**So that** 可以检测市场收益率的"可预测性上升"——临界慢化的直接推论

**技术实现:**

```python
# backend/src/cci_monitor/signals/autocorr.py
import pandas as pd
from ..core.exceptions import InsufficientDataError

def compute_autocorrelation(
    returns: pd.Series,
    window: int = 60,
    threshold: float = 0.15,
    min_periods: int = 10,
) -> pd.DataFrame:
    """
    计算滚动 AR(1) 自相关信号.
    
    Args:
        returns: 日收益率序列
        window: 滚动窗口(默认 60 日)
        threshold: 触发阈值(默认 0.15,健康市场接近 0)
        min_periods: 窗口内最少有效数据点
    
    Returns:
        DataFrame:
            - ar1: Lag-1 自相关系数
            - triggered: ar1 > threshold
    """
    if len(returns) < window:
        raise InsufficientDataError(
            f"need at least {window} bars, got {len(returns)}"
        )
    
    def ar1(x: pd.Series) -> float:
        x = x.dropna()
        if len(x) < min_periods:
            return float('nan')
        return x.autocorr(lag=1)
    
    ar1_series = returns.rolling(window).apply(ar1, raw=False)
    
    return pd.DataFrame({
        'ar1': ar1_series,
        'triggered': ar1_series > threshold,
    })
```

**验收标准:**
- [ ] 白噪音序列 → ar1 ≈ 0(|ar1| < 0.1)
- [ ] 强自相关序列(r_t = 0.5 × r_{t-1} + ε) → ar1 ≈ 0.5
- [ ] 数据不足抛 `InsufficientDataError`
- [ ] 单元测试覆盖所有边界

**预计工时:** 2 小时

**依赖:** Epic 0

---

#### Story 2.3: 信号 ③ 偏度信号

**As a** 开发者
**I want** 实现收益率偏度信号
**So that** 可以检测买卖力量结构的根本性变化

**技术实现:**

```python
# backend/src/cci_monitor/signals/skewness.py
import pandas as pd
from scipy import stats
from ..core.exceptions import InsufficientDataError

def compute_skewness_flip(
    returns: pd.Series,
    window: int = 60,
    threshold: float = 1.0,
    flip_threshold: float = 1.5,
    flip_window: int = 20,
) -> pd.DataFrame:
    """
    计算偏度及其翻转信号.
    
    逻辑: 健康市场偏度接近 0.
    偏度绝对值大 = 分布严重偏斜 → 买卖力量失衡.
    偏度快速翻转 = 市场性质根本变化.
    
    Args:
        returns: 日收益率序列
        window: 计算偏度的滚动窗口
        threshold: 偏度绝对值阈值
        flip_threshold: 翻转变化幅度阈值
        flip_window: 翻转检测窗口
    
    Returns:
        DataFrame:
            - skewness: 滚动偏度
            - skew_change: 相比 flip_window 日前的变化
            - triggered: 绝对值超阈 OR 翻转超阈
    """
    if len(returns) < window:
        raise InsufficientDataError(
            f"need at least {window} bars, got {len(returns)}"
        )
    
    skew_series = returns.rolling(window).skew()
    skew_change = skew_series.diff(flip_window)
    
    triggered = (skew_series.abs() > threshold) | (skew_change.abs() > flip_threshold)
    
    return pd.DataFrame({
        'skewness': skew_series,
        'skew_change': skew_change,
        'triggered': triggered,
    })
```

**验收标准:**
- [ ] 正态分布样本 → 偏度接近 0
- [ ] 右偏分布(指数分布)→ 偏度 > 1
- [ ] 偏度从 -1 变为 +1(翻转幅度 2)→ triggered=True
- [ ] 单元测试覆盖

**预计工时:** 2 小时

**依赖:** Epic 0

---

#### Story 2.4: 信号 ④ 横截面相关性 ⭐⭐⭐ **整个项目的基石**

> ⚠️ **这是 MVP 的最高优先级 Story,也是整个项目中技术难度、性能要求、业务价值最高的单个 Story。**
>
> **所有 CCI 计算、分层监测、历史回测、仪表盘核心图表都依赖它。**
>
> **建议留出完整 1-2 天时间集中开发,不要碎片化推进。**

**As a** 开发者
**I want** 高性能地计算多股票横截面相关性 ρ̄
**So that** 我可以检测市场个股独立定价能力的消失——临界状态最敏感的前兆

**业务价值:**

横截面相关性 ρ̄ 是 A 股临界预警中**最敏感的单一信号**。其核心逻辑:
- 正常市场:个股基于自身基本面/资金面独立定价 → ρ̄ 低(0.2-0.35)
- 临界状态:某个主导因子(流动性/恐慌/量化)压过个股特质 → ρ̄ 升(>0.5)
- 相变时刻:ρ̄ 可能突破 0.65+,表明所有股票被同一因子拖拽

这是其他三条信号都无法替代的独特维度。

**技术规范:**

```python
# backend/src/cci_monitor/signals/correlation.py
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Literal
from ..core.exceptions import InsufficientDataError, SignalError
from ..core.logger import logger


@dataclass(frozen=True)
class CrossCorrelationResult:
    """横截面相关性完整结果."""
    rho_bar: pd.Series       # 总体 ρ̄
    rho_up: pd.Series        # 涨日 ρ̄
    rho_down: pd.Series      # 跌日 ρ̄
    delta_rho: pd.Series     # Δρ̄ = ρ̄(t) - ρ̄(t-20)
    up_down_ratio: pd.Series # ρ̄_down / ρ̄_up
    pattern: pd.Series       # 形态分类
    sample_size: pd.Series   # 每日实际用于计算的股票数


def compute_rho_bar_fast(
    returns_matrix: np.ndarray,
    window: int = 20,
    min_stocks: int = 10,
    min_valid_ratio: float = 0.8,
) -> np.ndarray:
    """
    ⭐ 核心实现 · 矢量化横截面相关性计算.
    
    关键约束:
    - 必须使用 numpy 矢量化,不能用 pandas.corr() 循环
    - 300 股 × 250 天性能必须 < 3 秒
    - 正确处理 NaN 值和 std=0 的退化情况
    
    Args:
        returns_matrix: (T, N) numpy 数组, T=天数, N=股票数
        window: 滚动窗口
        min_stocks: 窗口内有效股票数下限
        min_valid_ratio: 单股票在窗口内的数据完整率要求
    
    Returns:
        (T,) 数组, 前 window 个为 NaN
    
    算法步骤(每个时间点 t):
        1. 取窗口数据 R = returns_matrix[t-window:t]
        2. 筛选完整率 ≥ min_valid_ratio 的股票列
        3. 标准化: (x - mean) / std,处理 std=0 情况
        4. 相关矩阵 = X^T @ X / (window - 1)
        5. 取上三角(不含对角)均值 → ρ̄(t)
    """
    T, N = returns_matrix.shape
    result = np.full(T, np.nan)
    
    if T < window:
        return result
    
    for t in range(window, T):
        win = returns_matrix[t-window:t]
        
        valid_ratio_per_col = np.isfinite(win).sum(axis=0) / window
        col_mask = valid_ratio_per_col >= min_valid_ratio
        
        if col_mask.sum() < min_stocks:
            continue
        
        win_filtered = win[:, col_mask]
        mean = np.nanmean(win_filtered, axis=0)
        centered = win_filtered - mean
        std = np.nanstd(centered, axis=0)
        std_valid = std > 1e-10
        if std_valid.sum() < min_stocks:
            continue
        
        X = centered[:, std_valid] / std[std_valid]
        X = np.nan_to_num(X, nan=0.0)
        n_valid = std_valid.sum()
        corr = (X.T @ X) / (window - 1)
        mask = np.triu(np.ones((n_valid, n_valid), dtype=bool), k=1)
        result[t] = corr[mask].mean()
    
    return result


def compute_cross_correlation(
    returns_wide: pd.DataFrame,
    window: int = 20,
    min_stocks: int = 10,
) -> CrossCorrelationResult:
    """
    完整的横截面相关性计算.
    包含 ρ̄ 主序列、分方向 ρ̄、Δρ̄、形态分类.
    
    详细说明参见 Technical Spec.
    """
    if len(returns_wide) < window + 20:
        raise InsufficientDataError(
            f"need at least {window + 20} bars, got {len(returns_wide)}"
        )
    
    dates = returns_wide.index
    returns_matrix = returns_wide.values
    
    rho_bar_arr = compute_rho_bar_fast(returns_matrix, window, min_stocks)
    rho_bar = pd.Series(rho_bar_arr, index=dates, name='rho_bar')
    
    market_ret = returns_wide.mean(axis=1)
    
    # 分方向计算 rho_up / rho_down
    rho_up_list = []
    rho_down_list = []
    for t in range(len(dates)):
        if t < window:
            rho_up_list.append(np.nan)
            rho_down_list.append(np.nan)
            continue
        
        win_ret = market_ret.iloc[t-window:t]
        win_data = returns_wide.iloc[t-window:t]
        
        up_mask = win_ret > 0
        down_mask = win_ret < 0
        
        if up_mask.sum() >= 5:
            rho_up_list.append(_compute_rho_single(win_data[up_mask].values, min_stocks))
        else:
            rho_up_list.append(np.nan)
        
        if down_mask.sum() >= 5:
            rho_down_list.append(_compute_rho_single(win_data[down_mask].values, min_stocks))
        else:
            rho_down_list.append(np.nan)
    
    rho_up = pd.Series(rho_up_list, index=dates, name='rho_up')
    rho_down = pd.Series(rho_down_list, index=dates, name='rho_down')
    
    delta_rho = rho_bar.diff(20)
    up_down_ratio = rho_down / rho_up
    pattern = _classify_patterns(rho_bar, market_ret, returns_wide)
    sample_size = returns_wide.notna().sum(axis=1)
    
    return CrossCorrelationResult(
        rho_bar=rho_bar,
        rho_up=rho_up,
        rho_down=rho_down,
        delta_rho=delta_rho,
        up_down_ratio=up_down_ratio,
        pattern=pattern,
        sample_size=sample_size,
    )


def _compute_rho_single(data: np.ndarray, min_stocks: int = 10) -> float:
    """单窗口 ρ̄ 计算(用于分方向场景)."""
    if len(data) < 2:
        return float('nan')
    
    valid_ratio = np.isfinite(data).sum(axis=0) / len(data)
    col_mask = valid_ratio >= 0.8
    if col_mask.sum() < min_stocks:
        return float('nan')
    
    data_f = data[:, col_mask]
    mean = np.nanmean(data_f, axis=0)
    centered = data_f - mean
    std = np.nanstd(centered, axis=0)
    std_valid = std > 1e-10
    if std_valid.sum() < min_stocks:
        return float('nan')
    
    X = centered[:, std_valid] / std[std_valid]
    X = np.nan_to_num(X, nan=0.0)
    n = std_valid.sum()
    corr = (X.T @ X) / (len(data_f) - 1)
    mask = np.triu(np.ones((n, n), dtype=bool), k=1)
    return float(corr[mask].mean())


def _classify_patterns(
    rho_bar: pd.Series,
    market_ret: pd.Series,
    returns_wide: pd.DataFrame,
    high_rho_threshold: float = 0.45,
    rally_return_threshold: float = 0.3,
    crash_return_threshold: float = -0.3,
) -> pd.Series:
    """
    形态分类: 
        A_rally    - 齐涨型(ρ̄ 高 + 市场涨)       · 健康,介质变深
        B_crash    - 齐跌型(ρ̄ 高 + 市场跌)       · 恐慌,相变警报
        C_crowding - 齐震型(ρ̄ 高 + 市场横盘)     · 拥挤,定时炸弹
        normal     - 正常
    """
    market_5d = market_ret.rolling(5).mean()
    pattern = pd.Series('normal', index=rho_bar.index, dtype=object)
    high_rho = rho_bar > high_rho_threshold
    
    pattern[high_rho & (market_5d > rally_return_threshold)] = 'A_rally'
    pattern[high_rho & (market_5d < crash_return_threshold)] = 'B_crash'
    pattern[high_rho & (market_5d.abs() <= rally_return_threshold)] = 'C_crowding'
    
    return pattern
```

**正确性验证测试:**

```python
# tests/unit/test_correlation.py
import numpy as np
from cci_monitor.signals.correlation import compute_rho_bar_fast, compute_cross_correlation

def test_rho_bar_independent_stocks():
    """独立随机序列 ρ̄ 应接近 0."""
    np.random.seed(42)
    returns = np.random.randn(250, 50)
    rho = compute_rho_bar_fast(returns, window=20)
    valid_rho = rho[~np.isnan(rho)]
    assert abs(np.mean(valid_rho)) < 0.1

def test_rho_bar_synchronized_stocks():
    """完全同步序列 ρ̄ 应接近 1."""
    base = np.random.randn(250, 1)
    returns = np.tile(base, (1, 50))
    rho = compute_rho_bar_fast(returns, window=20)
    valid_rho = rho[~np.isnan(rho)]
    assert np.mean(valid_rho) > 0.95

def test_rho_bar_partial_correlation():
    """有明显相关性但非完全同步."""
    np.random.seed(0)
    common = np.random.randn(250, 1)
    idiosync = np.random.randn(250, 50)
    returns = 0.5 * common + 0.5 * idiosync
    rho = compute_rho_bar_fast(returns, window=20)
    mean_rho = np.mean(rho[~np.isnan(rho)])
    assert 0.4 < mean_rho < 0.6

def test_rho_bar_handles_nans():
    """部分 NaN 不崩溃."""
    returns = np.random.randn(250, 50)
    returns[:100, :10] = np.nan
    rho = compute_rho_bar_fast(returns, window=20)
    assert not np.isnan(rho[-1])
```

**性能基准测试:**

```python
# tests/unit/test_correlation_performance.py
import numpy as np
import time
import pytest

@pytest.mark.benchmark
def test_performance_300x250():
    """核心基准: 300 股 × 250 天 < 3 秒."""
    np.random.seed(42)
    returns = np.random.randn(250, 300)
    t0 = time.time()
    rho = compute_rho_bar_fast(returns, window=20)
    elapsed = time.time() - t0
    assert elapsed < 3.0, f"性能未达标: {elapsed:.2f}s"
```

**真实数据验证:**

```python
# tests/integration/test_correlation_real_data.py
@pytest.mark.integration
async def test_real_hs300_rho_bar_range():
    """真实沪深300 ρ̄ 应在 0.1-0.8 之间."""
    source = AkshareDataSource()
    codes = (await source.fetch_index_components('000300'))[:50]
    returns_wide = await source.fetch_stocks_batch(codes, date.today() - timedelta(days=365))
    result = compute_cross_correlation(returns_wide, window=20)
    rho_clean = result.rho_bar.dropna()
    assert 0.05 < rho_clean.min() < rho_clean.max() < 0.85
    assert 0.15 < rho_clean.mean() < 0.65
```

**验收标准(严格):**

**功能正确性(必须全部通过):**
- [ ] 独立随机序列测试:|平均 ρ̄| < 0.1
- [ ] 完全同步序列测试:平均 ρ̄ > 0.95
- [ ] 50/50 混合因子测试:0.4 < 平均 ρ̄ < 0.6(理论值 0.5)
- [ ] NaN 容错测试通过
- [ ] 有效股票数不足时返回 NaN 不抛异常
- [ ] `CrossCorrelationResult` 所有字段都有正确计算
- [ ] 形态分类(A/B/C/normal)逻辑正确

**性能(硬性要求):**
- [ ] ⭐ **300 股 × 250 天计算 < 3 秒**(核心要求)
- [ ] 500 股 × 500 天计算 < 10 秒
- [ ] 内存使用合理,无泄漏
- [ ] 无 pandas.corr() 循环调用

**集成验证:**
- [ ] 用真实沪深300数据计算,结果在合理区间
- [ ] 能识别出 2024.01 微盘崩盘、2024.09 政策反弹等历史形态
- [ ] 三种形态(A/B/C)都能被正确标注

**代码质量:**
- [ ] 完整类型注解
- [ ] 完整 docstring 包含 Args/Returns/Raises/Example
- [ ] 关键算法步骤有中文注释
- [ ] 通过 ruff 和 mypy 检查

**预计工时:** **8-12 小时**(分 2 天集中开发,不要碎片化)

**分阶段开发建议:**

| 小时数 | 任务 |
|---|---|
| 0-2h | 读懂算法,跑通 `compute_rho_bar_fast` 主函数 |
| 2-4h | 写正确性单元测试,验证三种边界情况 |
| 4-6h | 性能优化,确保达到 3 秒基准 |
| 6-8h | 实现 `compute_cross_correlation` 完整版(含分方向) |
| 8-10h | 实现形态分类 `_classify_patterns` |
| 10-12h | 真实数据集成测试 + 可视化验证 |

**依赖:** Story 1.2(需要 akshare 拉取真实数据验证)

**下游依赖(都阻塞在本 Story):**
- Story 2.5 CCI 合成(使用 ρ̄ 和分方向 ρ̄)
- Story 3.2-3.7 六层分层(每层都要计算 ρ̄)
- Story 4.2 回测引擎(需要历史 ρ̄ 序列)
- Story 5.4 主仪表盘(ρ̄ 是核心图表)

---

#### Story 2.5: CCI 合成指数

**As a** 开发者
**I want** 将四条信号合成为单一 CCI 数值
**So that** 可以给出直观的 0-2 区间预警指标

**技术实现:**

```python
# backend/src/cci_monitor/signals/cci.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from ..core.exceptions import ConfigurationError


@dataclass(frozen=True)
class CCIResult:
    date: date
    cci: float
    alpha: float
    beta: float
    gamma: float
    delta: float
    alert_level: int
    alert_label: str
    market_rho: float
    resonant_rho: float | None
    deep_rho: float | None
    delta_rho: float | None
    up_down_ratio: float | None
    computed_at: datetime


def compute_cci(
    market_rho: float,
    resonant_rho: float | None = None,
    deep_rho: float | None = None,
    delta_rho: float | None = None,
    up_down_ratio: float | None = None,
    weights: dict[str, float] | None = None,
    computed_for_date: date | None = None,
) -> CCIResult:
    """
    计算 CCI 合成指数.
    
    公式:
        CCI = α_weight × (market_rho / 0.5)
            + β_weight × max(resonant_rho / deep_rho, 1.0)
            + γ_weight × max(delta_rho / 0.15, 0)
            + δ_weight × max(up_down_ratio, 1.0)
    """
    w = weights or {'alpha': 0.4, 'beta': 0.3, 'gamma': 0.2, 'delta': 0.1}
    
    if abs(sum(w.values()) - 1.0) > 1e-6:
        raise ConfigurationError(
            f"weights must sum to 1.0, got {sum(w.values())}"
        )
    
    alpha = w['alpha'] * (market_rho / 0.5)
    
    if resonant_rho is not None and deep_rho is not None and deep_rho > 1e-6:
        beta = w['beta'] * max(resonant_rho / deep_rho, 1.0)
    else:
        beta = w['beta']
    
    if delta_rho is not None:
        gamma = w['gamma'] * max(delta_rho / 0.15, 0)
    else:
        gamma = 0.0
    
    if up_down_ratio is not None:
        delta = w['delta'] * max(up_down_ratio, 1.0)
    else:
        delta = w['delta']
    
    cci = alpha + beta + gamma + delta
    alert_level, alert_label = classify_alert_level(cci)
    
    return CCIResult(
        date=computed_for_date or date.today(),
        cci=round(cci, 4),
        alpha=round(alpha, 4),
        beta=round(beta, 4),
        gamma=round(gamma, 4),
        delta=round(delta, 4),
        alert_level=alert_level,
        alert_label=alert_label,
        market_rho=market_rho,
        resonant_rho=resonant_rho,
        deep_rho=deep_rho,
        delta_rho=delta_rho,
        up_down_ratio=up_down_ratio,
        computed_at=datetime.now(),
    )


def classify_alert_level(cci: float) -> tuple[int, str]:
    if cci < 0.7:  return 0, "安全"
    if cci < 1.0:  return 1, "关注"
    if cci < 1.3:  return 2, "警戒"
    else:          return 3, "临界"
```

**验收标准:**
- [ ] baseline 场景(market_rho=0.25, resonant/deep=0.78, delta=0.05, ratio=1.1):CCI 在 0.5-0.9
- [ ] 临界场景(market_rho=0.65, resonant/deep=1.33, delta=0.20, ratio=1.8):CCI > 1.3 且 alert_level=3
- [ ] 权重和不为 1 → 抛 `ConfigurationError`
- [ ] 缺失可选参数使用中性值

**预计工时:** 3 小时

**依赖:** Story 2.4

---

#### Story 2.6: 每日计算服务(⭐ Milestone 2 Checkpoint)

**As a** 开发者
**I want** 一个完整的 daily_service 把前面的东西串起来
**So that** 能从命令行跑一次完整流程并把 CCI 入库

**技术实现:**

```python
# backend/src/cci_monitor/services/daily_service.py
from datetime import date, timedelta
from ..data.akshare_source import AkshareDataSource
from ..data.cache import CachedDataSource, Cache
from ..signals.correlation import compute_cross_correlation
from ..signals.cci import compute_cci, CCIResult
from ..db.models import CCIRecord
from ..core.database import get_db_session
from ..core.logger import logger
from config.settings import get_settings


class DailyService:
    def __init__(self):
        settings = get_settings()
        cache = Cache(settings.data.cache_dir, settings.data.cache_ttl_hours)
        self.source = CachedDataSource(AkshareDataSource(), cache)
        self.settings = settings
    
    async def run_daily(self, target_date: date | None = None) -> CCIResult:
        target_date = target_date or date.today()
        logger.info("Starting daily computation for {date}", date=target_date)
        
        start_date = target_date - timedelta(days=120)
        
        # 1. 拉取成分股
        codes = await self.source.fetch_index_components('000300')
        top_codes = codes[:self.settings.signal.correlation_stock_count]
        
        # 2. 批量拉取
        returns_wide = await self.source.fetch_stocks_batch(top_codes, start_date, target_date)
        
        # 3. 横截面相关性
        cc_result = compute_cross_correlation(
            returns_wide,
            window=self.settings.signal.correlation_window,
        )
        
        # 4. 取最新一天的指标
        market_rho = float(cc_result.rho_bar.iloc[-1])
        delta_rho = float(cc_result.delta_rho.iloc[-1]) if not cc_result.delta_rho.iloc[-1] != cc_result.delta_rho.iloc[-1] else None
        up = cc_result.rho_up.iloc[-1]
        down = cc_result.rho_down.iloc[-1]
        up_down_ratio = float(down / up) if up > 0 else None
        
        # 5. 合成 CCI
        cci_result = compute_cci(
            market_rho=market_rho,
            delta_rho=delta_rho,
            up_down_ratio=up_down_ratio,
            computed_for_date=target_date,
        )
        logger.info("CCI={cci} {label}", cci=cci_result.cci, label=cci_result.alert_label)
        
        # 6. 写入数据库
        async with get_db_session() as session:
            record = CCIRecord(
                date=cci_result.date,
                layer_id=1,
                cci=cci_result.cci,
                alpha=cci_result.alpha,
                beta=cci_result.beta,
                gamma=cci_result.gamma,
                delta=cci_result.delta,
                alert_level=cci_result.alert_level,
                alert_label=cci_result.alert_label,
                market_rho=cci_result.market_rho,
                delta_rho=cci_result.delta_rho,
                up_down_ratio=cci_result.up_down_ratio,
                computed_at=cci_result.computed_at,
            )
            session.add(record)
        
        return cci_result
```

**CLI 入口:**

```python
# backend/scripts/run_daily.py
import asyncio
from cci_monitor.services.daily_service import DailyService
from cci_monitor.core.logger import setup_logging

async def main():
    setup_logging()
    service = DailyService()
    result = await service.run_daily()
    print(f"\n=== 今日 CCI ===")
    print(f"日期: {result.date}")
    print(f"CCI:  {result.cci}")
    print(f"等级: {result.alert_label}")
    print(f"α={result.alpha} β={result.beta} γ={result.gamma} δ={result.delta}")

if __name__ == "__main__":
    asyncio.run(main())
```

**验收标准(⭐ Milestone 2 Checkpoint):**
- [ ] 运行 `python scripts/run_daily.py` 完整流程无错误
- [ ] 输出今日 CCI 数值在合理范围(0-2)
- [ ] 数据库 `cci_records` 表有新记录
- [ ] 运行两次不会重复插入(UniqueConstraint 生效)
- [ ] 全流程耗时 < 5 分钟(含数据拉取)

**预计工时:** 3 小时

**依赖:** Story 2.4, 2.5, 1.2, 1.3, 0.5

---

## Epic 3: 分层监测架构

### Story 3.1: Layer 抽象基类 (2h)
### Story 3.2: L1 全市场层 (4h)
### Story 3.3: L2 风格层 (6h)
### Story 3.4: L3 行业层 (5h)
### Story 3.5: L4 主题层 (6h) — **可延后**
### Story 3.6: L5/L6 龙头个股层 (4h) — **可延后**
### Story 3.7: 层级错位检测 (4h)

---

## Epic 4: 历史回测与校准

### Story 4.1: 历史事件标注 (3-4h)
### Story 4.2: 回测引擎 (6-8h)
### Story 4.3: 参数敏感性分析 (4h)
### Story 4.4: 回测结果持久化到数据库 (2h)

---

## Epic 5: Web 仪表盘

### Epic 目标

构建**生产级 Web 仪表盘**。与 Streamlit 不同,这是完整的 React SPA,样式和交互更精细。

### Stories

---

#### Story 5.1: 前端项目初始化

**技术选型说明:**

使用 **Vite + React 18 + TypeScript + TailwindCSS + shadcn/ui**,理由:
- Vite 开发体验最佳,构建快
- TailwindCSS 实现 Volume XI 配色最直接
- shadcn/ui 组件质量高且可定制
- TypeScript 降低 bug 率

**初始化步骤:**

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# shadcn-ui
npx shadcn-ui@latest init

# 依赖
npm install react-router-dom zustand @tanstack/react-query axios recharts d3 date-fns
npm install -D @types/d3
```

**TailwindCSS 主题配置(对齐 Volume XI 深色风格):**

```typescript
// tailwind.config.ts
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // === 深色背景 ===
        'bg':       '#0a0906',
        'bg-elev':  '#13100b',
        'bg-deep':  '#1a1610',
        'bg-inner': '#1f1a12',
        
        // === 文字 ===
        'ink':      '#f2ead8',
        'ink-dim':  '#c9bfa8',
        'ink-soft': '#8d8575',
        
        // === 强调色 ===
        'accent':   '#d65d43',
        'gold':     '#e0b663',
        'green':    '#7fbba3',
        'blue':     '#6fa8d0',
        'purple':   '#b88cd0',
        
        // === 警报色 ===
        'alert-safe':     '#7fbba3',
        'alert-attention':'#e0b663',
        'alert-warning':  '#d65d43',
        'alert-critical': '#e87060',
        
        // === 层级色 ===
        'layer-1': '#d65d43',
        'layer-2': '#e0b663',
        'layer-3': '#7fbba3',
        'layer-4': '#6fa8d0',
        'layer-5': '#b88cd0',
        'layer-6': '#8d8575',
        
        // === 线条 ===
        'line':      '#332d22',
        'line-soft': '#241f17',
      },
      fontFamily: {
        'serif': ['"Noto Serif SC"', 'serif'],
        'display': ['"Cormorant Garamond"', 'serif'],
        'mono': ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
};
```

**验收标准:**
- [ ] `npm run dev` 启动开发服务器
- [ ] TailwindCSS 主题色与 Volume XI 对齐
- [ ] 有基础的路由框架(Dashboard / Layers / Backtest / Settings)

**预计工时:** 4 小时

---

#### Story 5.2: API 客户端与数据层

**技术实现:**

```typescript
// src/services/api.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 10000,
});

// 响应拦截
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export interface CCIResponse {
  date: string;
  layer_id: number;
  cci: number;
  alpha: number;
  beta: number;
  gamma: number;
  delta: number;
  alert_level: number;
  alert_label: string;
  market_rho: number;
  resonant_rho: number | null;
  deep_rho: number | null;
  delta_rho: number | null;
  up_down_ratio: number | null;
}

export const api = {
  getLatestCCI: (layer: number = 1): Promise<CCIResponse> =>
    apiClient.get(`/api/v1/cci/latest?layer=${layer}`),
  
  getCCIHistory: (layer: number, start: string, end: string): Promise<CCIResponse[]> =>
    apiClient.get(`/api/v1/cci/history`, { params: { layer, start, end } }),
  
  getAllLayers: (): Promise<CCIResponse[]> =>
    apiClient.get(`/api/v1/layers/latest`),
  
  getBacktestResult: (): Promise<BacktestResponse> =>
    apiClient.get(`/api/v1/backtest/latest`),
  
  getSystemHealth: (): Promise<HealthResponse> =>
    apiClient.get(`/api/v1/system/health`),
};
```

**使用 React Query 管理数据:**

```typescript
// src/hooks/useCCI.ts
import { useQuery } from '@tanstack/react-query';

export function useLatestCCI(layer: number = 1) {
  return useQuery({
    queryKey: ['cci', 'latest', layer],
    queryFn: () => api.getLatestCCI(layer),
    staleTime: 60_000,  // 1 分钟内不重复请求
    refetchInterval: 5 * 60_000,  // 每 5 分钟刷新
  });
}
```

**验收标准:**
- [ ] 所有 API 响应有完整 TypeScript 类型
- [ ] 使用 React Query 缓存和自动刷新
- [ ] 错误状态有统一处理

**预计工时:** 3 小时

---

#### Story 5.3: CCI 仪表盘半圆图

**技术实现:**

使用 recharts RadialBarChart 或自定义 SVG。推荐自定义 SVG 以完全控制视觉。

```typescript
// src/components/charts/CCIGauge.tsx
interface Props {
  cci: number;
  alertLevel: number;
  size?: number;
}

export function CCIGauge({ cci, alertLevel, size = 280 }: Props) {
  // 映射 CCI 值到角度 (0 → -90°, 2 → 90°)
  const angle = Math.min(Math.max(cci / 2, 0), 1) * 180 - 90;
  const color = getAlertColor(alertLevel);
  
  return (
    <svg viewBox="0 0 280 200" className="w-full">
      {/* 渐变定义 */}
      <defs>
        <linearGradient id="gaugeGrad">
          <stop offset="0%" stopColor="#7fbba3" />
          <stop offset="50%" stopColor="#e0b663" />
          <stop offset="80%" stopColor="#d65d43" />
          <stop offset="100%" stopColor="#e87060" />
        </linearGradient>
      </defs>
      
      {/* 背景弧 */}
      <path
        d="M 40 160 A 100 100 0 0 1 240 160"
        fill="none"
        stroke="url(#gaugeGrad)"
        strokeWidth="20"
        strokeLinecap="round"
      />
      
      {/* 刻度标签 */}
      {/* ... */}
      
      {/* 指针 */}
      <g transform={`rotate(${angle} 140 160)`}>
        <line
          x1="140" y1="160"
          x2="140" y2="70"
          stroke="#f2ead8"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <circle cx="140" cy="160" r="10" fill={color} stroke="#f2ead8" strokeWidth="2" />
      </g>
      
      {/* 中心标签 */}
      <text x="140" y="190" textAnchor="middle" className="font-display italic" fill={color}>
        CCI {cci.toFixed(2)}
      </text>
    </svg>
  );
}
```

**验收标准:**
- [ ] 与 Volume XI 文档中的仪表盘视觉一致
- [ ] 指针平滑动画过渡
- [ ] 响应式(适配不同尺寸)

**预计工时:** 4 小时

---

#### Story 5.4: 主仪表盘页面

**页面布局:**

```
┌─────────────────────────────────────────────────┐
│  Sidebar     │   TopBar (刷新按钮 · 当前时间)     │
│  - Dashboard │─────────────────────────────────  │
│  - Layers    │                                    │
│  - Backtest  │   ┌──────────┐  ┌──────────────┐  │
│  - Settings  │   │          │  │ CCI 历史曲线  │  │
│              │   │  CCI 仪表 │  │ 60 天         │  │
│              │   │          │  │              │  │
│              │   └──────────┘  └──────────────┘  │
│              │                                    │
│              │   ┌──────────────────────────────┐ │
│              │   │    四分量条形图              │ │
│              │   │    α · β · γ · δ            │ │
│              │   └──────────────────────────────┘ │
│              │                                    │
│              │   ┌──────────────────────────────┐ │
│              │   │  ρ̄ 时间序列 + 形态ABC标记   │ │
│              │   └──────────────────────────────┘ │
│              │                                    │
│              │   ┌──────────────────────────────┐ │
│              │   │  六层 CCI 热力图             │ │
│              │   └──────────────────────────────┘ │
│              │                                    │
│              │   ┌──────────────────────────────┐ │
│              │   │  最近预警列表                │ │
│              │   └──────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**验收标准:**
- [ ] 所有图表数据来自 API
- [ ] 响应式,移动端可用
- [ ] 加载时有 skeleton 占位
- [ ] 页面首屏加载 < 2 秒

**预计工时:** 8-10 小时

---

#### Story 5.5: 分层监测页面 (6h)
#### Story 5.6: 回测页面 (6h)
#### Story 5.7: 设置页面 (3h)

---

## Epic 6: 调度与推送

### Story 6.1: 每日定时任务 (4h)

```python
# backend/src/cci_monitor/scheduler/main.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ..services.daily_service import DailyService
from ..core.logger import logger

async def main():
    scheduler = AsyncIOScheduler()
    service = DailyService()
    
    # 交易日 17:00 运行
    scheduler.add_job(
        service.run_daily,
        CronTrigger(day_of_week='mon-fri', hour=17, minute=0),
        id='daily_cci_computation',
        max_instances=1,  # 防止重复
    )
    
    # 每小时健康检查
    scheduler.add_job(
        service.health_check,
        CronTrigger(minute=0),
        id='hourly_health_check',
    )
    
    scheduler.start()
    logger.info("Scheduler started")
    
    # 保持运行
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        scheduler.shutdown()
```

### Story 6.2: 多通道推送 (4h)

支持 Server 酱 + SMTP + Bark。**带防骚扰机制**。

```python
# backend/src/cci_monitor/scheduler/notifier.py
class Notifier:
    async def send_alert(self, alert: AlertRecord):
        # 去重检查(24h 内同级别不重复推送)
        if self._is_duplicate(alert):
            return
        
        # 多通道并发推送
        results = await asyncio.gather(
            self._send_server_chan(alert),
            self._send_email(alert),
            return_exceptions=True,
        )
        
        # 至少一个成功即算成功
        if any(not isinstance(r, Exception) for r in results):
            self._record_sent(alert)
```

### Story 6.3: 日报生成 (3h)

---

## Epic 7: API 层

### Epic 目标

构建 **REST API**,供前端和第三方系统调用。

### Stories

---

#### Story 7.1: FastAPI 应用骨架

```python
# backend/src/cci_monitor/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .v1 import cci, layers, backtest, system
from ..core.logger import setup_logging, logger
from ..core.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("API starting")
    yield
    await engine.dispose()
    logger.info("API shutdown")

app = FastAPI(
    title="CCI Monitor API",
    description="A股相变监测 REST API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://cci.yourdomain.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 路由
app.include_router(cci.router, prefix="/api/v1/cci", tags=["cci"])
app.include_router(layers.router, prefix="/api/v1/layers", tags=["layers"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["backtest"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])

# 统一错误处理
from ..core.exceptions import CCIError

@app.exception_handler(CCIError)
async def cci_error_handler(request, exc: CCIError):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.code,
            "message": str(exc),
            "context": exc.context,
        },
    )
```

**预计工时:** 3 小时

---

#### Story 7.2: 核心 API 端点

**端点清单:**

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/cci/latest` | 最新 CCI |
| GET | `/api/v1/cci/history` | CCI 历史(支持 layer 过滤) |
| GET | `/api/v1/layers/latest` | 所有层级最新快照 |
| GET | `/api/v1/layers/{id}/history` | 指定层级历史 |
| GET | `/api/v1/layers/{id}/components` | 层级监测对象 |
| GET | `/api/v1/backtest/latest` | 最新回测结果 |
| POST | `/api/v1/backtest/run` | 触发回测 |
| GET | `/api/v1/alerts/recent` | 最近预警 |
| GET | `/api/v1/dislocations/recent` | 最近层级错位 |
| GET | `/api/v1/system/health` | 健康检查 |
| POST | `/api/v1/system/refresh` | 手动触发计算 |

**预计工时:** 6 小时

---

#### Story 7.3: API 认证与限流 (3h)

即使个人使用,也要最基本的 API Key 保护。使用 FastAPI Security + slowapi。

---

## 里程碑与迭代计划

基于你的情况(Python 熟练 + 10+ 小时/周 + 完整系统需求),**6-8 周是合理的节奏**。

### Milestone 1 · 地基(第 1-2 周) — **20-25 小时**

**目标:** 跑通从数据到 CCI 数值的完整链条

| Story | 工时 |
|---|---|
| 0.1 项目初始化 | 2h |
| 0.2 配置系统 | 3h |
| 0.3 日志 | 2h |
| 0.4 异常 | 1h |
| 0.5 数据库 & ORM | 4h |
| 1.1 DataSource 抽象 | 2h |
| 1.2 akshare 实现 | 8h |
| 1.3 缓存 | 4h |

**Checkpoint:** 
```bash
$ python -c "from cci_monitor.data import get_source; import asyncio; print(asyncio.run(get_source().fetch_index_daily('sh000300', date(2024,1,1))))"
# 能成功输出沪深300数据
```

---

### Milestone 2 · 核心指标(第 2-3 周) — **25-30 小时**

**目标:** 能算出 CCI 并落库

⭐ **本 Milestone 的核心是 Story 2.4(横截面相关性),它决定了整个项目的技术上限。**
建议第一个完整工作日集中攻克 Story 2.4,其余 Story 在其之上叠加。

| Story | 工时 | 优先级 |
|---|---|---|
| 1.4 弹性层 | 3h | 必需 |
| **2.4 横截面相关性 ⭐⭐⭐** | **8-12h** | **MVP 基石,最高优先级** |
| 2.1 方差信号 | 2h | 必需 |
| 2.2 自相关信号 | 2h | 必需 |
| 2.3 偏度信号 | 2h | 必需 |
| 2.5 CCI 合成 | 3h | 必需(依赖 2.4) |
| 2.6 daily_service | 3h | ⭐ Milestone Checkpoint |
| 3.1 Layer 抽象 | 2h | 为 M3 做准备 |

**Checkpoint:**
```bash
$ python scripts/run_daily.py
# 输出:今日 CCI = 0.85 | 等级:一阶关注
# 数据已写入 cci_records 表
```

**⚠️ 特别提醒:**
- 不要为了赶进度而跳过 2.4 的性能基准测试
- 不要为了赶进度而跳过 2.4 的真实数据集成测试
- 2.4 没做完,不要开始 2.5 或任何下游 Story

---

### Milestone 3 · 分层与回测(第 4 周) — **20 小时**

| Story | 工时 |
|---|---|
| 3.3 L2 风格层 | 6h |
| 3.4 L3 行业层 | 5h |
| 3.7 层级错位 | 4h |
| 4.1 事件标注 | 3h |
| 4.2 回测引擎 | 6h |

**Checkpoint:** 有三层 CCI + 回测报告

---

### Milestone 4 · API 层(第 5 周) — **15 小时**

| Story | 工时 |
|---|---|
| 7.1 FastAPI 骨架 | 3h |
| 7.2 核心端点 | 6h |
| 7.3 认证限流 | 3h |
| 0.6 Docker | 4h |

**Checkpoint:** `curl http://localhost:8000/api/v1/cci/latest` 返回数据

---

### Milestone 5 · Web 仪表盘(第 6-7 周) — **30 小时**

| Story | 工时 |
|---|---|
| 5.1 前端初始化 | 4h |
| 5.2 API 客户端 | 3h |
| 5.3 CCI 仪表 | 4h |
| 5.4 主仪表盘 | 10h |
| 5.5 分层页面 | 6h |
| 5.6 回测页面 | 6h |

**Checkpoint:** 浏览器打开 http://localhost:3000 看到完整仪表盘

---

### Milestone 6 · 自动化(第 8 周) — **12 小时**

| Story | 工时 |
|---|---|
| 6.1 调度器 | 4h |
| 6.2 推送 | 4h |
| 6.3 日报生成 | 3h |
| 5.7 设置页面 | 3h |

**Checkpoint:** 每日 17:00 自动出日报,微信收到推送

---

### 总计:约 115-130 小时,8 周完成

**每周进度建议:**
- Week 1-2: 15h/周 · 地基
- Week 3-4: 15h/周 · 核心指标 + 分层
- Week 5: 15h · API
- Week 6-7: 15h/周 · 前端
- Week 8: 12h · 上线

如果每周投入 20h,可压缩到 6 周。

---

## Story 验收清单

每个 Story 完成时检查:

### 代码质量
- [ ] `ruff check .` 无警告
- [ ] `mypy backend/src/` 类型检查通过
- [ ] 公开函数有 docstring
- [ ] 无 TODO/FIXME(或有 GitHub Issue 跟踪)

### 测试
- [ ] 单元测试覆盖关键路径
- [ ] 测试覆盖率 ≥ 70%
- [ ] 集成测试标记 `@pytest.mark.integration`

### 文档
- [ ] README 或 docstring 有使用示例
- [ ] 关键决策有注释说明"为什么"

### 运行
- [ ] 干净环境可重现
- [ ] 错误处理完整
- [ ] 日志清晰

---

## 风险与缓解

| 风险 | 影响 | 概率 | 缓解 |
|---|---|---|---|
| akshare 接口频繁故障 | 高 | **高** | 缓存 + 重试 + 断路器 + 早期集成测试 |
| 横截面相关性性能不达标 | 中 | 低 | numpy 矢量化 + 早期基准测试 |
| 历史事件标注主观 | 中 | 高 | 交叉验证 + 敏感性分析 |
| 过拟合历史 | 高 | **高** | 训练/测试分离 + 样本外 |
| 前端工作量超估 | 中 | 中 | 先用 Streamlit 占位,再迁移 |
| 推送被平台封禁 | 低 | 低 | 多通道备份 + 防骚扰 |
| Docker 部署复杂 | 中 | 中 | 先本地开发,部署前 1 周再做 |

---

## 附录: 开发哲学

### 给 AI Agent 的核心指导

1. **先读文档再写代码** — README → Epic/Stories → Technical Spec
2. **严格按 Phase 顺序** — 前一 Milestone 必须完全通过再进入下一个
3. **每个 Story 完成后:**
   - 自己运行一次(不只是跑测试)
   - 检查验收标准逐项打勾
   - 更新 CHANGELOG
4. **遇到歧义:** 先查 Technical Spec,仍不清楚就问用户
5. **性能敏感代码必须基准测试** — 不要相信直觉

### 代码哲学

- **类型胜过文档** — 完整类型注解让代码自文档化
- **失败要喧嚣** — 异常必须抛,不要静默返回 None
- **配置不硬编码** — 所有阈值、权重、窗口从 Settings 读
- **日志像呼吸** — 每个关键节点都应该有日志
- **测试先行** — 计算逻辑必须有单元测试

---

**文档版本:** v2.0
**适配目标:** 完整系统 + 零预算 + Python 熟练 + 8 周交付
**下一步:** 在 Antigravity 中创建项目,按 Milestone 1 开始
