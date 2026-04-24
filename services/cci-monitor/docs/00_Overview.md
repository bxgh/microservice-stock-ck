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

