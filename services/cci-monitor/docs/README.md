# CCI Monitor

> A 股相变监测体系 — 完整系统版 (数据库 + Web + API + 定时推送)

基于临界慢化理论构建的 A 股市场预警系统。
**Docker 一键部署**,浏览器访问仪表盘,每日定时生成报告并推送微信。

---

## ✨ 核心特性

- 🎯 **四条独立预警信号** — 方差、自相关、偏度、横截面相关性
- 📊 **六层分层监测** — 从全市场到个股的完整覆盖
- 🌐 **完整系统** — PostgreSQL + FastAPI + React + 调度器
- 🔔 **智能推送** — 状态升级自动微信/邮件通知
- 📈 **历史回测** — Precision/Recall 可验证
- 🎨 **深色仪表盘** — 与研究文档 Vol.XI 视觉一致
- 🐳 **Docker 部署** — `docker-compose up` 一键启动

---

## 🚀 快速开始

### 方案 A: Docker 一键部署(推荐)

```bash
# 克隆仓库
git clone <repo_url> cci-monitor
cd cci-monitor

# 配置环境
cp .env.example .env
# 编辑 .env 填写必要配置(可选)

# 启动全部服务
docker-compose up -d

# 初始化数据库
docker-compose exec backend alembic upgrade head

# 首次手动触发计算
docker-compose exec backend python scripts/run_daily.py

# 访问仪表盘
open http://localhost:3000
```

### 方案 B: 本地开发

```bash
# 1. 启动 PostgreSQL
docker-compose up -d postgres

# 2. 后端
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn cci_monitor.api.main:app --reload

# 3. 前端(新终端)
cd frontend
npm install
npm run dev

# 4. 调度器(新终端,可选)
cd backend
uv run python scripts/start_scheduler.py
```

---

## 🏛️ 项目结构

```
cci-monitor/
├── docker-compose.yml           # 一键部署
├── .env.example                 # 配置模板
├── docs/                        # 完整文档
│   ├── CCI_Monitor_Epic_Stories.md     # 产品需求
│   ├── CCI_Monitor_Technical_Spec.md   # 技术规范
│   └── theory.md                # 理论背景
├── backend/                     # Python 后端
│   ├── src/cci_monitor/
│   │   ├── data/               # 数据源
│   │   ├── signals/            # 四条信号
│   │   ├── layers/             # 六层架构
│   │   ├── backtest/           # 回测
│   │   ├── api/                # FastAPI
│   │   ├── scheduler/          # 定时任务
│   │   └── services/           # 业务服务
│   └── tests/
├── frontend/                   # React 前端
│   └── src/
│       ├── pages/
│       ├── components/
│       └── services/
└── deploy/                     # 部署配置
    └── caddy/
```

---

## 🎨 核心公式

### CCI 合成指数

```
CCI = 0.4 × (ρ̄_market / 0.5)          α · 市场级相关性
    + 0.3 × max(ρ̄_resonant / ρ̄_deep, 1)  β · 介质反转
    + 0.2 × max(Δρ̄ / 0.15, 0)             γ · 斜率变化
    + 0.1 × max(ρ̄_down / ρ̄_up, 1)         δ · 方向分解
```

### 预警分级

| CCI | 等级 | 颜色 | 建议 |
|---|---|---|---|
| < 0.7 | 🟢 安全 | Green | 常规操作 |
| 0.7 – 1.0 | 🟡 关注 | Gold | 暂停加杠杆 |
| 1.0 – 1.3 | 🟠 警戒 | Orange | 开始减仓 |
| > 1.3 | 🔴 临界 | Red | 防御优先 |

---

## 🛠️ 技术栈

**后端:**
- Python 3.11 + FastAPI + SQLAlchemy 2.0 (async)
- PostgreSQL + APScheduler
- akshare (数据源) + loguru (日志)

**前端:**
- React 18 + TypeScript + Vite
- TailwindCSS + shadcn/ui
- React Query + Zustand + Recharts + D3

**部署:**
- Docker + docker-compose
- Caddy (反向代理 + 自动 HTTPS)

---

## 📖 文档导航

| 文档 | 用途 |
|---|---|
| `README.md` (本文件) | 项目简介 + 快速开始 |
| `docs/CCI_Monitor_Epic_Stories.md` | **完整 PRD + 开发任务(22+ Stories)** |
| `docs/CCI_Monitor_Technical_Spec.md` | **技术规范速查** |
| `docs/theory.md` | 理论背景(承接 Vol.XI) |

**给 AI Coding Agent:** 请优先阅读 Epic/Stories 和 Technical Spec。
所有实现细节(公式、接口、阈值、配色)都在这两份文档中。

---

## 📅 开发路线图

**总计 ≈ 8 周,每周 10-15 小时**

| 周次 | Milestone | 核心产出 |
|---|---|---|
| 1-2 | **M1 地基** | 项目骨架 + 数据层 |
| 2-3 | **M2 核心指标** ⭐ | **横截面相关性 ρ̄ + CCI 能算出并落库** |
| 4 | **M3 分层+回测** | L1-L3 + 回测报告 |
| 5 | **M4 API** | REST API + Docker 化 |
| 6-7 | **M5 前端** | 完整 Web 仪表盘 |
| 8 | **M6 自动化** | 调度器 + 微信推送 |

### ⭐ 核心基础:Story 2.4 横截面相关性

**整个项目有一个数学基石:横截面相关性 ρ̄ 的计算(Story 2.4)**。

它是:
- CCI 四个分量(α/β/γ/δ)的共同输入
- 六层分层监测每一层的核心指标  
- 历史回测的基础数据
- 仪表盘的核心图表

**Story 2.4 完成度 = 项目上限。** 建议分 2 天集中投入,按三阶段开发:
1. 核心算法 `compute_rho_bar_fast`(性能 300股×250天<3秒)
2. 完整 `compute_cross_correlation`(含形态分类)
3. 真实数据集成验证

详见 `docs/CCI_Monitor_Epic_Stories.md` 中的 Story 2.4 完整说明。

详细 Story 拆解见 `docs/CCI_Monitor_Epic_Stories.md`。

---

## 🎯 API 端点速览

```
GET  /api/v1/cci/latest?layer=1
GET  /api/v1/cci/history?layer=1&start=2024-01-01&end=2026-04-20
GET  /api/v1/layers/latest
GET  /api/v1/layers/{id}/history
GET  /api/v1/backtest/latest
GET  /api/v1/alerts/recent
GET  /api/v1/system/health
POST /api/v1/system/refresh
```

自动生成的 OpenAPI 文档: http://localhost:8000/docs

---

## 🔔 推送配置

编辑 `.env` 添加任一推送方式:

**Server 酱 (微信,推荐):**
```bash
NOTIFICATION__SERVER_CHAN_KEY=SCT....
```

**SMTP 邮件:**
```bash
NOTIFICATION__SMTP_HOST=smtp.gmail.com
NOTIFICATION__SMTP_USER=your@email.com
NOTIFICATION__SMTP_PASSWORD=app_password
NOTIFICATION__SMTP_TO=recipient@email.com
```

---

## 🤝 理论基础

基于 Marten Scheffer 2009 年在 Nature 发表的**临界慢化理论**,
并结合 A 股"九类资金博弈"的独特结构本土化改造。

**核心洞察:**
> 外力决定是否有波 · 介质决定波有多大 · **临界点决定波何时断**

详见 `docs/theory.md` 和研究系列 Volume X / XI。

---

## 🏗️ 开发工具

**推荐:**
- **Antigravity** - AI 驱动的 IDE,本项目专为此优化
- **uv** 或 **poetry** - Python 依赖管理
- **pgAdmin** 或 **DBeaver** - 数据库管理

**Agent 使用指南:**
1. 先读 `docs/README.md` 和 `docs/CCI_Monitor_Epic_Stories.md`
2. 按 Milestone 顺序开发,不要跳跃
3. 每完成一个 Story 先跑测试再进入下一个
4. 遇到技术细节查 `docs/CCI_Monitor_Technical_Spec.md`

---

## ⚠️ 免责声明

- 本系统仅供**个人研究与学习**使用
- **不构成任何投资建议**
- 历史回测不代表未来表现
- 使用者需自行承担一切投资风险

---

## 📄 License

MIT License

---

**项目起源:** A股资金博弈研究体系 · Volume XI
**开发环境:** Antigravity + Claude + 8 周 Sprint
**当前版本:** 1.0.0 (规划阶段)
