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

建立基于 **MySQL 数据接口 (get-stockdata API)** 的稳定数据获取层。详细规范见 [data-layer.md](file:///home/bxgh/microservice-stock/docs/CCI_monitor/data-layer.md)。
不再直接从互联网抓取原始数据，而是消费内部已同步的结构化数据。

### Stories

---

#### Story 1.1: DataSource 抽象基类 (API 版)

**技术实现:**

参照 [data-layer.md](file:///home/bxgh/microservice-stock/docs/CCI_monitor/data-layer.md) 定义的 `DataSource` 抽象接口，确保兼容 MySQL API 的返回格式。

**验收标准:**
- [ ] 接口规范使用 async/await
- [ ] 支持按代码和日期范围批量请求 API
- [ ] 有完整的 docstring 包含返回格式映射

**预计工时:** 2 小时

---

#### Story 1.2: MySQL API 数据源实现

**技术实现:**

实现 `MySQLDataClient`。
- 使用 `httpx` 调用内部 `get-stockdata` 接口。
- 实现指数日线、个股日线、成分股列表的获取逻辑。
- 处理 API 返回的 JSON 并转换为 `pandas.DataFrame`。
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

*(此 Epic 的 Story 与 v1 基本一致,以下为精简版以节省篇幅,详细内容参考 Technical Spec 文档)*

### Story 2.1: 信号 ① 波动率方差上升 (2h)
### Story 2.2: 信号 ② 自相关性 (2h)
### Story 2.3: 信号 ③ 偏度信号 (2h)
### Story 2.4: 信号 ④ 横截面相关性 (6-8h) ⭐ **核心**

**关键性能要求:** 300 股 × 250 天计算 < 3 秒

**必须使用 numpy 矢量化实现,不能用 pandas.corr() 循环**

### Story 2.5: CCI 合成指数 (3h)

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

### Milestone 2 · 核心指标(第 2-3 周) — **20-25 小时**

**目标:** 能算出 CCI 并落库

| Story | 工时 |
|---|---|
| 1.4 弹性层 | 3h |
| 2.1-2.3 三条信号 | 6h |
| 2.4 横截面相关性 ⭐ | 8h |
| 2.5 CCI 合成 | 3h |
| 3.1 Layer 抽象 | 2h |
| 3.2 L1 层 | 4h |
| services/daily_service | 2h |

**Checkpoint:**
```bash
$ python scripts/run_daily.py
# 输出:今日 CCI = 0.85 | 等级:一阶关注
# 数据已写入 cci_records 表
```

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
